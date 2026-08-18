"""The tray: one icon per tracked series, and a deliberately tiny menu.

Menu design follows the brief literally — the only top-level entries are the
three settings plus Quit:

    Manga ▸  ·  Language ▸  ·  ☑ Start on login  ·  Quit

Anything series-specific (open the chapter, mark it read) only appears when it
is actually actionable, so the normal resting state of the menu is those four
lines. Adding, removing and forcing a check live inside the Manga submenu,
which keeps the top level from growing.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices
from PySide6.QtWidgets import QApplication, QInputDialog, QMenu, QSystemTrayIcon

from mangame.domain.models import IconState, SeriesSnapshot
from mangame.domain.state import aggregate
from mangame.i18n.catalog import Translator, available
from mangame.service import autostart
from mangame.service.library import Library
from mangame.service.poller import PollOutcome
from mangame.sources.base import SourceMatch
from mangame.store import config
from mangame.store.config import SeriesConfig, Settings
from mangame.store.db import Database
from mangame.ui.emblems import icon_for
from mangame.ui.worker import PollWorker, SearchWorker

LOG = logging.getLogger(__name__)

#: How often the tray re-derives state. Cheap (no network): a series can move
#: from "waiting" to "due" purely because time passed.
REFRESH_MS = 60_000

NOTIFY_MS = 8_000

#: Titles we ship real artwork for. Everything else gets a generated monogram.
EMBLEM_HINTS: dict[str, str] = {"one piece": "strawhat"}

#: Sources worth attaching automatically when a series is added.
PREFERRED_SOURCES = ("mangadex", "anilist", "mangaupdates")


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "series"


def emblem_for(title: str) -> str:
    lowered = title.lower()
    for needle, emblem in EMBLEM_HINTS.items():
        if needle in lowered:
            return emblem
    return "monogram"


class MangameTray(QObject):
    """Owns every tray icon and the menu they share."""

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self._db = Database()
        self._settings = config.load()
        self._library = Library(self._settings, self._db)
        self._t = Translator(self._settings.language)

        self._icons: dict[str, QSystemTrayIcon] = {}
        self._menus: dict[int, QMenu] = {}
        self._last_state: dict[str, IconState] = {}
        self._search: SearchWorker | None = None

        self._worker = PollWorker()
        self._worker.outcomes.connect(self._on_outcomes)

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_MS)
        self._timer.timeout.connect(self.refresh)

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        self.refresh()
        self._timer.start()
        self._worker.start()

    def shutdown(self) -> None:
        self._timer.stop()
        self._worker.stop()
        self._worker.wait(5_000)
        for icon in self._icons.values():
            icon.hide()
        self._db.close()

    # --------------------------------------------------------------- refresh

    def _reload_settings(self) -> None:
        self._settings = config.load()
        self._library.replace_settings(self._settings)
        self._t = Translator(self._settings.language)

    def _save(self, settings: Settings) -> None:
        config.save(settings)
        self._reload_settings()
        self.refresh()

    def refresh(self) -> None:
        """Recompute every snapshot and reconcile the tray icons with it."""
        now = datetime.now(UTC)
        snapshots = {s.key: s for s in self._library.snapshots(now)}
        visible = [c for c in self._settings.tray_series() if c.key in snapshots]

        if self._settings.single_tray_icon or not visible:
            self._render_single(list(snapshots.values()))
            return

        self._destroy_icon("__all__")
        for series_config in visible:
            self._render_series(snapshots[series_config.key])
        for key in set(self._icons) - {c.key for c in visible}:
            self._destroy_icon(key)

    def _render_single(self, snapshots: list[SeriesSnapshot]) -> None:
        """Fallback/aggregate mode: one hat that speaks for the whole library."""
        for key in set(self._icons) - {"__all__"}:
            self._destroy_icon(key)

        state = aggregate([s.icon_state for s in snapshots])
        icon = self._ensure_icon("__all__")
        icon.setIcon(icon_for("strawhat", state, "mangame"))
        icon.setToolTip("\n".join(s.tooltip for s in snapshots) or self._t("menu.no_series"))
        icon.setContextMenu(self._build_menu(icon, None))
        icon.show()

    def _render_series(self, snapshot: SeriesSnapshot) -> None:
        icon = self._ensure_icon(snapshot.key)
        icon.setIcon(icon_for(snapshot.emblem, snapshot.icon_state, snapshot.title))
        icon.setToolTip(snapshot.tooltip)
        icon.setContextMenu(self._build_menu(icon, snapshot))
        icon.show()
        self._last_state[snapshot.key] = snapshot.icon_state

    def _ensure_icon(self, key: str) -> QSystemTrayIcon:
        icon = self._icons.get(key)
        if icon is None:
            icon = QSystemTrayIcon(self)
            icon.activated.connect(lambda _reason, k=key: self._on_activated(k))
            self._icons[key] = icon
        return icon

    def _destroy_icon(self, key: str) -> None:
        icon = self._icons.pop(key, None)
        if icon is not None:
            self._menus.pop(id(icon), None)
            icon.hide()
            icon.deleteLater()

    # ------------------------------------------------------------------ menu

    def _build_menu(self, owner: QSystemTrayIcon, snapshot: SeriesSnapshot | None) -> QMenu:
        # QSystemTrayIcon is not a QWidget, so the menu cannot be parented to
        # it. Keeping a reference here is what stops Python from collecting a
        # menu that Qt is still showing.
        menu = QMenu()
        self._menus[id(owner)] = menu

        if snapshot is not None:
            header = menu.addAction(f"{snapshot.title} — {self._state_label(snapshot)}")
            header.setEnabled(False)

            if snapshot.icon_state is IconState.READY and snapshot.latest_chapter:
                chapter = snapshot.latest_chapter
                label = self._t("menu.open")
                if chapter.number:
                    label = f"{label} {chapter.number}"
                open_action = menu.addAction(label)
                open_action.triggered.connect(lambda: self._open(snapshot.key))

                read_action = menu.addAction(self._t("menu.mark_read"))
                read_action.triggered.connect(lambda: self._mark_read(snapshot.key))
            menu.addSeparator()

        menu.addMenu(self._manga_menu(menu))
        menu.addMenu(self._language_menu(menu))

        boot = menu.addAction(self._t("menu.autostart"))
        boot.setCheckable(True)
        boot.setChecked(autostart.is_enabled())
        boot.setEnabled(autostart.is_supported())
        boot.toggled.connect(self._set_autostart)

        menu.addSeparator()
        quit_action = menu.addAction(self._t("menu.quit"))
        quit_action.triggered.connect(self._quit)
        return menu

    def _manga_menu(self, parent: QMenu) -> QMenu:
        menu = QMenu(self._t("menu.manga"), parent)

        if not self._settings.series:
            empty = menu.addAction(self._t("menu.no_series"))
            empty.setEnabled(False)
        for series_config in self._settings.series:
            action = menu.addAction(series_config.title)
            action.setCheckable(True)
            action.setChecked(series_config.show_in_tray)
            action.toggled.connect(
                lambda checked, key=series_config.key: self._toggle_tray(key, checked)
            )

        menu.addSeparator()
        add = menu.addAction(self._t("menu.add"))
        add.triggered.connect(self._add_series)

        if self._settings.series:
            remove = QMenu(self._t("menu.remove"), menu)
            for series_config in self._settings.series:
                action = remove.addAction(series_config.title)
                action.triggered.connect(
                    lambda _checked=False, key=series_config.key: self._remove(key)
                )
            menu.addMenu(remove)

        check = menu.addAction(self._t("menu.refresh"))
        check.triggered.connect(self._worker.request_check_now)
        return menu

    def _language_menu(self, parent: QMenu) -> QMenu:
        menu = QMenu(self._t("menu.language"), parent)
        group = QActionGroup(menu)
        group.setExclusive(True)

        for code, label in available().items():
            action = QAction(label, menu)
            action.setCheckable(True)
            action.setChecked(code == self._t.language)
            action.triggered.connect(lambda _checked=False, chosen=code: self._set_language(chosen))
            group.addAction(action)
            menu.addAction(action)
        return menu

    def _state_label(self, snapshot: SeriesSnapshot) -> str:
        return self._t(f"state.{snapshot.icon_state.value}")

    # --------------------------------------------------------------- actions

    def _set_language(self, code: str) -> None:
        settings = self._settings.model_copy(update={"language": code})
        self._save(settings)

    def _set_autostart(self, enabled: bool) -> None:
        if autostart.set_enabled(enabled):
            self._save(self._settings.model_copy(update={"autostart": enabled}))

    def _toggle_tray(self, key: str, checked: bool) -> None:
        series = [
            s.model_copy(update={"show_in_tray": checked}) if s.key == key else s
            for s in self._settings.series
        ]
        self._save(self._settings.model_copy(update={"series": series}))

    def _remove(self, key: str) -> None:
        self._db.forget_series(key)
        series = [s for s in self._settings.series if s.key != key]
        self._destroy_icon(key)
        self._save(self._settings.model_copy(update={"series": series}))

    def _open(self, key: str) -> None:
        snapshot = self._library.snapshot_for(key, datetime.now(UTC))
        if snapshot and snapshot.latest_chapter and snapshot.latest_chapter.url:
            QDesktopServices.openUrl(QUrl(snapshot.latest_chapter.url))
        self._mark_read(key)

    def _mark_read(self, key: str) -> None:
        self._library.mark_read(key)
        self.refresh()

    def _on_activated(self, key: str) -> None:
        """Left-click. Only meaningful where the platform delivers it."""
        state = self._last_state.get(key)
        if state is IconState.READY:
            self._open(key)

    def _quit(self) -> None:
        self.shutdown()
        self._app.quit()

    # ------------------------------------------------------------ add series

    def _add_series(self) -> None:
        query, accepted = QInputDialog.getText(
            None, self._t("dialog.add.title"), self._t("dialog.add.prompt")
        )
        if not accepted or not query.strip():
            return

        self._search = SearchWorker(query.strip())
        self._search.found.connect(self._on_search_results)
        self._search.start()

    def _on_search_results(self, matches: list[SourceMatch]) -> None:
        if not matches:
            QInputDialog.getItem(
                None,
                self._t("dialog.add.title"),
                self._t("dialog.add.none"),
                [""],
                editable=False,
            )
            return

        labels = [self._label_for(m) for m in matches]
        chosen, accepted = QInputDialog.getItem(
            None,
            self._t("dialog.add.title"),
            self._t("dialog.add.prompt"),
            labels,
            editable=False,
        )
        if not accepted:
            return
        self._track(matches[labels.index(chosen)], matches)

    @staticmethod
    def _label_for(match: SourceMatch) -> str:
        year = f" ({match.year})" if match.year else ""
        return f"{match.title}{year}  ·  {match.source_id}"

    def _track(self, chosen: SourceMatch, everything: list[SourceMatch]) -> None:
        """Attach the chosen match plus any same-titled match from other sources.

        Cross-linking matters: MangaDex supplies chapter times while AniList
        supplies the hiatus flag, and a series needs both to use all three
        icon states.
        """
        key = slugify(chosen.title)
        if any(s.key == key for s in self._settings.series):
            return

        sources = {chosen.source_id: chosen.ref}
        normalised = chosen.title.strip().lower()
        for candidate in everything:
            if candidate.source_id in sources:
                continue
            if candidate.source_id not in PREFERRED_SOURCES:
                continue
            if candidate.title.strip().lower() == normalised:
                sources[candidate.source_id] = candidate.ref

        entry = SeriesConfig(
            key=key,
            title=chosen.title,
            emblem=emblem_for(chosen.title),
            sources=sources,
        )
        self._save(self._settings.model_copy(update={"series": [*self._settings.series, entry]}))
        self._worker.request_check_now()

    # --------------------------------------------------------- notifications

    def _on_outcomes(self, outcomes: list[PollOutcome]) -> None:
        previous = dict(self._last_state)
        self.refresh()

        if not self._settings.notifications:
            return

        for outcome in outcomes:
            snapshot = outcome.snapshot
            if snapshot is None:
                continue
            icon = self._icons.get(snapshot.key) or next(iter(self._icons.values()), None)
            if icon is None:
                continue

            if outcome.new_chapters > 0 and snapshot.icon_state is IconState.READY:
                chapter = snapshot.latest_chapter
                suffix = f" {chapter.number}" if chapter and chapter.number else ""
                icon.showMessage(
                    self._t("notify.new_chapter"),
                    f"{snapshot.title}{suffix}",
                    QSystemTrayIcon.MessageIcon.Information,
                    NOTIFY_MS,
                )
            elif (
                snapshot.icon_state is IconState.BREAK
                and previous.get(snapshot.key) is not IconState.BREAK
            ):
                reason = snapshot.active_break.reason if snapshot.active_break else ""
                icon.showMessage(
                    self._t("notify.break"),
                    f"{snapshot.title} — {reason}".strip(" —"),
                    QSystemTrayIcon.MessageIcon.Information,
                    NOTIFY_MS,
                )

"""The tray: one icon per tracked series, and a deliberately tiny menu.

The menu holds verbs only — the things you *do*:

    [Series — state]  ·  Open chapter  ·  Mark as read
    Add manga…  ·  Check now  ·  Settings…  ·  Quit

Anything series-specific only appears when it is actually actionable, so the
resting state is those four lines. Everything with a *value* — the language,
the switches, which series show an icon, which emblem each wears — lives in
:mod:`mangame.ui.settings_dialog` instead.

That split is deliberate. The menu used to nest three deep (Manga ▸ Stop
tracking ▸ a series), which is slow to reach and, on a panel pinned to a screen
edge, prone to running off the display entirely. A flat list of verbs cannot.

Either mouse button opens it. An icon in a panel shows nothing but a picture,
so whichever button someone tries first has to arrive somewhere — and with the
values moved out, there is only one somewhere left to arrive at.
"""

import logging
from datetime import UTC, datetime

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import QApplication, QDialog, QMenu, QSystemTrayIcon

from mangame.domain.models import IconState, SeriesSnapshot
from mangame.domain.state import aggregate
from mangame.i18n.catalog import Translator
from mangame.service import autostart
from mangame.service.library import Library
from mangame.service.poller import PollOutcome
from mangame.sources import registry
from mangame.sources.base import SourceMatch
from mangame.store import config
from mangame.store.config import SeriesConfig, Settings, series_key
from mangame.store.db import Database
from mangame.ui.add_dialog import AddSeriesDialog, SeriesCandidate
from mangame.ui.emblems import icon_for
from mangame.ui.menu import TrayMenu, menu_anchor
from mangame.ui.settings_dialog import SettingsDialog
from mangame.ui.worker import PollWorker, SearchWorker

LOG = logging.getLogger(__name__)

#: How often the tray re-derives state. Cheap (no network): a series can move
#: from "waiting" to "due" purely because time passed.
REFRESH_MS = 60_000

NOTIFY_MS = 8_000

#: Titles we ship real artwork for. Everything else gets a generated monogram.
EMBLEM_HINTS: dict[str, str] = {"one piece": "onepiece"}

#: Sources worth attaching automatically when a series is added.
PREFERRED_SOURCES = ("mangadex", "anilist", "mangaupdates")

#: Clicks that raise the menu. Not ``Context``: the platform already raises it
#: for the right button. Not ``MiddleClick`` either — a menu appearing under a
#: button nobody aimed with is a surprise, not a shortcut.
OPENS_MENU = frozenset(
    {
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.DoubleClick,
    }
)


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
        self._searches: set[SearchWorker] = set()
        self._dialog: AddSeriesDialog | None = None
        self._settings_dialog: SettingsDialog | None = None
        self._relanguage = False

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
        for search in tuple(self._searches):
            search.wait(5_000)
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
        """Aggregate mode: one icon that speaks for the whole library.

        It wears its own emblem rather than any series', and shows the
        aggregate state, so "something is ready" is still one glance.
        """
        for key in set(self._icons) - {"__all__"}:
            self._destroy_icon(key)

        state = aggregate([s.icon_state for s in snapshots])
        icon = self._ensure_icon("__all__")
        icon.setIcon(icon_for(self._settings.tray_emblem, state, "mangame"))
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
            icon.activated.connect(lambda reason, k=key: self._on_activated(k, reason))
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
        #
        # Which is also why an open one is left alone. The tray re-derives
        # state every minute; replacing the menu then drops the last reference
        # to the one under the pointer, and Qt deletes it mid-click. A minute
        # of staleness is the cheaper failure — and the better behaviour
        # anyway, since items do not move while you are reaching for them.
        showing = self._menus.get(id(owner))
        if showing is not None and showing.isVisible():
            return showing

        menu = TrayMenu()
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

        add = menu.addAction(self._t("menu.add"))
        add.triggered.connect(self._add_series)

        check = menu.addAction(self._t("menu.refresh"))
        check.triggered.connect(self._worker.request_check_now)

        settings = menu.addAction(self._t("menu.settings"))
        settings.triggered.connect(self._open_settings)

        menu.addSeparator()
        quit_action = menu.addAction(self._t("menu.quit"))
        quit_action.triggered.connect(self._quit)
        return menu

    def _state_label(self, snapshot: SeriesSnapshot) -> str:
        return self._t(f"state.{snapshot.icon_state.value}")

    # -------------------------------------------------------------- settings

    def _open_settings(self) -> None:
        """Show the settings window, reopening it if the language changed.

        Modal for the same reason the add dialog is: ``exec()`` runs a nested
        event loop, which is what delivers queued signals from the search
        thread while a window is up.
        """
        if self._settings_dialog is not None:
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return

        while self._run_settings():
            # The language is also the UI language, so a fresh dialog is the
            # honest way to show the choice taking effect.
            pass

    def _run_settings(self) -> bool:
        dialog = SettingsDialog(
            self._t,
            self._settings,
            autostart_enabled=autostart.is_enabled(),
            autostart_supported=autostart.is_supported(),
        )
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.autostart_changed.connect(self._set_autostart)
        dialog.add_requested.connect(lambda: self._add_series(dialog))
        dialog.remove_requested.connect(self._remove)
        dialog.artwork_changed.connect(self.refresh)

        self._settings_dialog = dialog
        self._relanguage = False
        try:
            dialog.exec()
        finally:
            self._settings_dialog = None
        return self._relanguage

    def _on_settings_changed(self, settings: Settings) -> None:
        """Persist what the dialog changed, reacting to a language switch.

        Changing the reading language changes *what gets polled*, not just the
        wording, so everything owed is re-asked immediately instead of waiting
        out the schedule the previous language left behind.
        """
        relanguage = settings.language != self._settings.language
        self._save(settings)
        if relanguage:
            self._worker.request_check_now()
            self._relanguage = True
            if self._settings_dialog is not None:
                self._settings_dialog.accept()

    # --------------------------------------------------------------- actions

    def _set_autostart(self, enabled: bool) -> None:
        if autostart.set_enabled(enabled):
            self._save(self._settings.model_copy(update={"autostart": enabled}))

    def _remove(self, key: str) -> None:
        self._db.forget_series(key)
        self._destroy_icon(key)
        self._save(self._settings.without_series(key))
        self._resync_settings_dialog()

    def _resync_settings_dialog(self) -> None:
        """Push a changed series list back into an open settings window."""
        if self._settings_dialog is not None:
            self._settings_dialog.set_settings(self._settings)

    def _open(self, key: str) -> None:
        snapshot = self._library.snapshot_for(key, datetime.now(UTC))
        if snapshot and snapshot.latest_chapter and snapshot.latest_chapter.url:
            QDesktopServices.openUrl(QUrl(snapshot.latest_chapter.url))
        self._mark_read(key)

    def _mark_read(self, key: str) -> None:
        self._library.mark_read(key)
        self.refresh()

    def _on_activated(self, key: str, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Open the menu on a left click, the same one the right button gives.

        Two buttons, one menu. A tray icon has no other affordance — there is
        nothing to see on it but the picture — so the click people try first
        has to lead somewhere, and the menu is the only somewhere there is.

        Left click used to open the newest chapter when one was waiting. That
        was invisible (nothing says an icon is clickable, let alone that it is
        clickable *sometimes*) and, in aggregate mode, dead: the state it
        consulted is only recorded per series. The menu still offers it, spelt
        out, one line down.

        ``Context`` is deliberately not handled: Qt raises the context menu for
        the right button itself, and popping it a second time would fight that.
        """
        if reason not in OPENS_MENU:
            return
        icon = self._icons.get(key)
        menu = icon.contextMenu() if icon is not None else None
        if icon is not None and menu is not None:
            menu.popup(menu_anchor(icon.geometry(), QCursor.pos()))

    def _quit(self) -> None:
        self.shutdown()
        self._app.quit()

    # ------------------------------------------------------------ add series

    def _add_series(self, parent: QDialog | None = None) -> None:
        """Open the one window that searches and adds.

        Modal on purpose: ``exec()`` runs a nested event loop, which is what
        delivers the search thread's queued signal while the dialog is up.
        """
        dialog = AddSeriesDialog(self._t, [s.key for s in self._settings.series], parent)
        dialog.search_requested.connect(lambda query: self._run_search(dialog, query))
        self._dialog = dialog
        try:
            accepted = dialog.exec() == QDialog.DialogCode.Accepted
        finally:
            self._dialog = None

        if accepted and dialog.chosen is not None:
            self._track(dialog.chosen)

    def _run_search(self, dialog: AddSeriesDialog, query: str) -> None:
        worker = SearchWorker(query, self._settings.language)
        # Held until Qt says the thread finished. A QThread collected while it
        # is still running takes the process with it, and the dialog can be
        # closed — or searched again — before a slow source has answered.
        self._searches.add(worker)
        worker.found.connect(lambda matches: self._on_search_results(dialog, matches))
        worker.finished.connect(lambda: self._searches.discard(worker))
        worker.start()

    def _on_search_results(self, dialog: AddSeriesDialog, matches: list[SourceMatch]) -> None:
        if self._dialog is not dialog:
            return  # the dialog was closed while the search was in flight
        dialog.show_results(matches)

    def _track(self, candidate: SeriesCandidate) -> None:
        """Attach every source that offered this series and can serve it.

        Cross-linking matters: MangaDex supplies chapter times while AniList
        supplies the hiatus flag, and a series needs both to use all three icon
        states. The dialog groups matches by title, so the sources linked here
        are exactly the ones the chosen row listed.
        """
        chosen = candidate.primary
        key = series_key(chosen.title)
        if any(s.key == key for s in self._settings.series):
            return

        language = self._settings.language
        sources = {chosen.source_id: chosen.ref}
        for match in candidate.matches:
            if match.source_id in sources or match.source_id not in PREFERRED_SOURCES:
                continue
            if registry.serves(match.source_id, language):
                sources[match.source_id] = match.ref

        entry = SeriesConfig(
            key=key,
            title=chosen.title,
            emblem=emblem_for(chosen.title),
            sources=sources,
        )
        self._save(self._settings.model_copy(update={"series": [*self._settings.series, entry]}))
        self._resync_settings_dialog()
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

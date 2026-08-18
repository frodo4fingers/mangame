"""The library: config + learned state + read state, folded into one view.

Both the poller and the tray read the world through this object, so there is
exactly one place that knows how a configured series, its stored chapters and
whatever the sources last said add up to something the icon can render.
"""

from collections.abc import Iterable
from datetime import datetime

from mangame.domain import breaks as break_rules
from mangame.domain import cadence as cadence_rules
from mangame.domain import state as state_rules
from mangame.domain.models import (
    PublicationStatus,
    SeriesSnapshot,
    SourceSignal,
    TrackedSeries,
)
from mangame.store.config import SeriesConfig, Settings
from mangame.store.db import Database, LearnedState

#: A definite answer beats "unknown"; a declared hiatus beats everything. This
#: ranking resolves *disagreement between sources within one poll* — it is
#: deliberately not applied across polls, because a series must be able to come
#: back off hiatus.
_STATUS_RANK = {
    PublicationStatus.UNKNOWN: 0,
    PublicationStatus.ONGOING: 1,
    PublicationStatus.COMPLETED: 2,
    PublicationStatus.CANCELLED: 2,
    PublicationStatus.HIATUS: 3,
}


class Library:
    """Reads and updates everything about the user's tracked series."""

    def __init__(self, settings: Settings, database: Database) -> None:
        self._settings = settings
        self._db = database

    @property
    def settings(self) -> Settings:
        return self._settings

    def replace_settings(self, settings: Settings) -> None:
        self._settings = settings

    def configs(self) -> list[SeriesConfig]:
        return [s for s in self._settings.series if s.enabled]

    def hydrate(self, config: SeriesConfig) -> TrackedSeries:
        """Assemble one fully-populated series from config + database."""
        language = self._settings.language_for(config)
        learned = self._db.load_learned(config.key)
        last_read_id, last_read_at = self._db.read_state(config.key)

        return TrackedSeries(
            key=config.key,
            title=config.title,
            emblem=config.emblem,
            language=language,
            enabled=config.enabled,
            show_in_tray=config.show_in_tray,
            source_refs=dict(config.sources),
            status=learned.status,
            cadence=learned.cadence,
            latest_chapter=self._db.latest_chapter(config.key, language=language),
            last_read_at=last_read_at,
            last_read_external_id=last_read_id,
            announced_next_at=learned.announced_next_at,
            breaks=learned.breaks,
        )

    def all_series(self) -> list[TrackedSeries]:
        return [self.hydrate(config) for config in self.configs()]

    def snapshots(self, now: datetime) -> list[SeriesSnapshot]:
        return [state_rules.resolve(series, now) for series in self.all_series()]

    def snapshot_for(self, key: str, now: datetime) -> SeriesSnapshot | None:
        for config in self.configs():
            if config.key == key:
                return state_rules.resolve(self.hydrate(config), now)
        return None

    def apply(self, config: SeriesConfig, signals: Iterable[SourceSignal], now: datetime) -> int:
        """Fold fresh source signals into stored state.

        Returns the number of genuinely new chapters, which is what decides
        whether a notification fires.
        """
        language = self._settings.language_for(config)
        signal_list = list(signals)

        new_chapters = 0
        for signal in signal_list:
            relevant = [
                chapter for chapter in signal.chapters if chapter.language in (language, "")
            ]
            new_chapters += self._db.record_chapters(config.key, relevant)

        learned = self._merge_learned(config, signal_list, language, now)
        self._db.save_learned(config.key, learned)
        return new_chapters

    def _merge_learned(
        self,
        config: SeriesConfig,
        signals: list[SourceSignal],
        language: str,
        now: datetime,
    ) -> LearnedState:
        previous = self._db.load_learned(config.key)

        # Rank only within this poll. Seeding from the previous status would
        # make HIATUS a ratchet that no later "ongoing" could ever undo, so a
        # series that came back would stay black forever. Sources that answered
        # "unknown" (or 304'd) simply do not vote, and the previous status
        # stands until something informative arrives.
        voted = [s.status for s in signals if s.status is not PublicationStatus.UNKNOWN]
        status = max(voted, key=lambda s: _STATUS_RANK[s]) if voted else previous.status

        history = self._db.chapters_for(config.key, language=language, limit=120)
        cadence = cadence_rules.estimate(history)
        last_release_at = history[0].published_at if history else None

        announced = next(
            (s.announced_next_at for s in signals if s.announced_next_at is not None),
            None,
        )

        candidates = list(previous.breaks)
        for signal in signals:
            candidates.extend(signal.breaks)
            window = break_rules.from_announced_next(
                announced_next_at=signal.announced_next_at,
                last_release_at=last_release_at,
                cadence=cadence,
                source_id=signal.source_id,
            )
            if window is not None:
                candidates.append(window)
            flagged = break_rules.from_status(
                status=signal.status, now=now, source_id=signal.source_id
            )
            if flagged is not None:
                candidates.append(flagged)

        # Drop windows that have already elapsed so the list cannot grow forever.
        live = [w for w in candidates if w.ends_at is None or w.ends_at > now]
        if status is not PublicationStatus.HIATUS:
            live = [w for w in live if w.ends_at is not None]

        return LearnedState(
            status=status,
            cadence=cadence,
            breaks=break_rules.merge(live),
            announced_next_at=announced or previous.announced_next_at,
        )

    def mark_read(self, key: str) -> None:
        config = next((c for c in self.configs() if c.key == key), None)
        if config is None:
            return
        language = self._settings.language_for(config)
        self._db.mark_read(key, self._db.latest_chapter(key, language=language))

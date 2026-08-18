"""SQLite persistence.

Plain :mod:`sqlite3` rather than an ORM: the schema is four tables, the whole
database lives in one local file, and avoiding SQLAlchemy + Alembic keeps both
the dependency tree and the packaged binary small — which matters a lot for a
tray utility. Schema evolution is handled by a tiny migration list keyed on
``PRAGMA user_version``.

Calls are synchronous. Local SQLite writes are measured in microseconds, so
blocking the poller's event loop for one is cheaper than the thread hop that
would avoid it.
"""

import json
import sqlite3
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Self

from pydantic import BaseModel, Field

from mangame.domain.models import BreakWindow, Cadence, Chapter, PublicationStatus
from mangame.store import paths

MIGRATIONS: Sequence[str] = (
    """
    CREATE TABLE series_state (
        series_key         TEXT PRIMARY KEY,
        status             TEXT NOT NULL DEFAULT 'unknown',
        cadence_json       TEXT,
        breaks_json        TEXT,
        announced_next_at  TEXT,
        updated_at         TEXT NOT NULL
    );

    CREATE TABLE chapter (
        series_key    TEXT NOT NULL,
        source_id     TEXT NOT NULL,
        external_id   TEXT NOT NULL,
        number        TEXT,
        volume        TEXT,
        title         TEXT,
        language      TEXT NOT NULL,
        published_at  TEXT NOT NULL,
        url           TEXT,
        PRIMARY KEY (series_key, source_id, external_id)
    );
    CREATE INDEX chapter_by_series ON chapter (series_key, published_at DESC);

    CREATE TABLE poll_state (
        series_key         TEXT NOT NULL,
        source_id          TEXT NOT NULL,
        next_due_at        TEXT,
        last_polled_at     TEXT,
        consecutive_errors INTEGER NOT NULL DEFAULT 0,
        tier               TEXT,
        etag               TEXT,
        last_modified      TEXT,
        watermark          TEXT,
        PRIMARY KEY (series_key, source_id)
    );

    CREATE TABLE read_state (
        series_key            TEXT PRIMARY KEY,
        last_read_external_id TEXT,
        last_read_at          TEXT
    );
    """,
)


class LearnedState(BaseModel):
    """What polling has taught us about one series."""

    status: PublicationStatus = PublicationStatus.UNKNOWN
    cadence: Cadence = Field(default_factory=Cadence)
    breaks: list[BreakWindow] = Field(default_factory=list)
    announced_next_at: datetime | None = None


class PollState(BaseModel):
    """Scheduling bookkeeping for one (series, source) pair."""

    series_key: str
    source_id: str
    next_due_at: datetime | None = None
    last_polled_at: datetime | None = None
    consecutive_errors: int = 0
    tier: str = ""
    etag: str | None = None
    last_modified: str | None = None
    watermark: str | None = None


def _iso(moment: datetime | None) -> str | None:
    return moment.astimezone(UTC).isoformat() if moment else None


def _parse(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).astimezone(UTC)
    except ValueError:
        return None


class Database:
    """Thin, typed wrapper over the state file."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or paths.database_file()
        self._connection = sqlite3.connect(self._path, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def _migrate(self) -> None:
        current = int(self._connection.execute("PRAGMA user_version").fetchone()[0])
        for version, script in enumerate(MIGRATIONS[current:], start=current + 1):
            self._connection.executescript(script)
            self._connection.execute(f"PRAGMA user_version = {version}")

    # ---------------------------------------------------------------- chapters

    def record_chapters(self, series_key: str, chapters: Iterable[Chapter]) -> int:
        """Upsert chapters; returns how many rows were genuinely new."""
        rows = [
            (
                series_key,
                c.source_id,
                c.external_id,
                c.number,
                c.volume,
                c.title,
                c.language,
                _iso(c.published_at),
                c.url,
            )
            for c in chapters
        ]
        if not rows:
            return 0
        before = self._count_chapters(series_key)
        self._connection.executemany(
            """
            INSERT INTO chapter (series_key, source_id, external_id, number, volume,
                                 title, language, published_at, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (series_key, source_id, external_id) DO UPDATE SET
                number = excluded.number,
                volume = excluded.volume,
                title = excluded.title,
                published_at = excluded.published_at,
                url = excluded.url
            """,
            rows,
        )
        return self._count_chapters(series_key) - before

    def _count_chapters(self, series_key: str) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) FROM chapter WHERE series_key = ?", (series_key,)
        ).fetchone()
        return int(row[0])

    def chapters_for(
        self, series_key: str, *, language: str | None = None, limit: int = 60
    ) -> list[Chapter]:
        """Most recent chapters first, optionally restricted to one language."""
        query = "SELECT * FROM chapter WHERE series_key = ?"
        params: list[object] = [series_key]
        if language:
            query += " AND language = ?"
            params.append(language)
        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)

        chapters: list[Chapter] = []
        for row in self._connection.execute(query, params):
            published = _parse(row["published_at"])
            if published is None:
                continue
            chapters.append(
                Chapter(
                    source_id=row["source_id"],
                    external_id=row["external_id"],
                    number=row["number"],
                    volume=row["volume"],
                    title=row["title"],
                    language=row["language"],
                    published_at=published,
                    url=row["url"],
                )
            )
        return chapters

    def latest_chapter(self, series_key: str, *, language: str | None = None) -> Chapter | None:
        found = self.chapters_for(series_key, language=language, limit=1)
        return found[0] if found else None

    # ------------------------------------------------------------ learned state

    def save_learned(self, series_key: str, state: LearnedState) -> None:
        self._connection.execute(
            """
            INSERT INTO series_state (series_key, status, cadence_json, breaks_json,
                                      announced_next_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (series_key) DO UPDATE SET
                status = excluded.status,
                cadence_json = excluded.cadence_json,
                breaks_json = excluded.breaks_json,
                announced_next_at = excluded.announced_next_at,
                updated_at = excluded.updated_at
            """,
            (
                series_key,
                state.status.value,
                state.cadence.model_dump_json(),
                json.dumps([b.model_dump(mode="json") for b in state.breaks]),
                _iso(state.announced_next_at),
                _iso(datetime.now(UTC)),
            ),
        )

    def load_learned(self, series_key: str) -> LearnedState:
        row = self._connection.execute(
            "SELECT * FROM series_state WHERE series_key = ?", (series_key,)
        ).fetchone()
        if row is None:
            return LearnedState()
        return LearnedState(
            status=PublicationStatus(row["status"]),
            cadence=(
                Cadence.model_validate_json(row["cadence_json"])
                if row["cadence_json"]
                else Cadence()
            ),
            breaks=[
                BreakWindow.model_validate(entry)
                for entry in json.loads(row["breaks_json"] or "[]")
            ],
            announced_next_at=_parse(row["announced_next_at"]),
        )

    # -------------------------------------------------------------- poll state

    def poll_state(self, series_key: str, source_id: str) -> PollState:
        row = self._connection.execute(
            "SELECT * FROM poll_state WHERE series_key = ? AND source_id = ?",
            (series_key, source_id),
        ).fetchone()
        if row is None:
            return PollState(series_key=series_key, source_id=source_id)
        return PollState(
            series_key=series_key,
            source_id=source_id,
            next_due_at=_parse(row["next_due_at"]),
            last_polled_at=_parse(row["last_polled_at"]),
            consecutive_errors=int(row["consecutive_errors"]),
            tier=row["tier"] or "",
            etag=row["etag"],
            last_modified=row["last_modified"],
            watermark=row["watermark"],
        )

    def save_poll_state(self, state: PollState) -> None:
        self._connection.execute(
            """
            INSERT INTO poll_state (series_key, source_id, next_due_at, last_polled_at,
                                    consecutive_errors, tier, etag, last_modified, watermark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (series_key, source_id) DO UPDATE SET
                next_due_at = excluded.next_due_at,
                last_polled_at = excluded.last_polled_at,
                consecutive_errors = excluded.consecutive_errors,
                tier = excluded.tier,
                etag = excluded.etag,
                last_modified = excluded.last_modified,
                watermark = excluded.watermark
            """,
            (
                state.series_key,
                state.source_id,
                _iso(state.next_due_at),
                _iso(state.last_polled_at),
                state.consecutive_errors,
                state.tier,
                state.etag,
                state.last_modified,
                state.watermark,
            ),
        )

    def due_pairs(self, now: datetime) -> set[tuple[str, str]]:
        """(series_key, source_id) pairs whose next poll is owed."""
        rows = self._connection.execute(
            "SELECT series_key, source_id FROM poll_state"
            " WHERE next_due_at IS NULL OR next_due_at <= ?",
            (_iso(now),),
        )
        return {(row["series_key"], row["source_id"]) for row in rows}

    def clear_due(self) -> None:
        """Make everything owed immediately, for an explicit "check now".

        Cache validators and watermarks go too. They describe the answer to the
        *previous* question, and the reading language is part of that question:
        MangaDex's ``latestUploadedChapter`` moves for any translation, so a
        reader who just switched to German would otherwise be told "nothing
        changed" and never see a German chapter arrive.
        """
        self._connection.execute(
            "UPDATE poll_state SET next_due_at = NULL, consecutive_errors = 0,"
            " etag = NULL, last_modified = NULL, watermark = NULL"
        )

    # -------------------------------------------------------------- read state

    def mark_read(self, series_key: str, chapter: Chapter | None) -> None:
        self._connection.execute(
            """
            INSERT INTO read_state (series_key, last_read_external_id, last_read_at)
            VALUES (?, ?, ?)
            ON CONFLICT (series_key) DO UPDATE SET
                last_read_external_id = excluded.last_read_external_id,
                last_read_at = excluded.last_read_at
            """,
            (
                series_key,
                chapter.external_id if chapter else None,
                _iso(datetime.now(UTC)),
            ),
        )

    def read_state(self, series_key: str) -> tuple[str | None, datetime | None]:
        row = self._connection.execute(
            "SELECT * FROM read_state WHERE series_key = ?", (series_key,)
        ).fetchone()
        if row is None:
            return None, None
        return row["last_read_external_id"], _parse(row["last_read_at"])

    # ----------------------------------------------------------------- upkeep

    def prune_chapters(self, keep_per_series: int = 200) -> None:
        """Cadence only ever looks at recent history; the rest is dead weight."""
        self._connection.execute(
            """
            DELETE FROM chapter WHERE rowid IN (
                SELECT rowid FROM (
                    SELECT rowid,
                           ROW_NUMBER() OVER (
                               PARTITION BY series_key ORDER BY published_at DESC
                           ) AS rank
                    FROM chapter
                ) WHERE rank > ?
            )
            """,
            (keep_per_series,),
        )

    def forget_series(self, series_key: str) -> None:
        for table in ("series_state", "chapter", "poll_state", "read_state"):
            self._connection.execute(
                f"DELETE FROM {table} WHERE series_key = ?",
                (series_key,),
            )

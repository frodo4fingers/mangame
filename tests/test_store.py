"""Persistence: SQLite state and the JSON settings file."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from mangame.domain.models import BreakWindow, Cadence, Chapter, Confidence, PublicationStatus
from mangame.store import config as config_store
from mangame.store import paths
from mangame.store.db import Database, LearnedState, PollState

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def chapter(number: str, offset_days: int, language: str = "en") -> Chapter:
    return Chapter(
        source_id="mangadex",
        external_id=f"ch-{number}-{language}",
        number=number,
        language=language,
        published_at=NOW - timedelta(days=offset_days),
        url=f"https://example.test/{number}",
    )


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    with Database(tmp_path / "mangame.db") as database:
        yield database


class TestChapters:
    def test_chapters_round_trip(self, db: Database) -> None:
        assert db.record_chapters("one-piece", [chapter("1190", 9), chapter("1189", 20)]) == 2
        stored = db.chapters_for("one-piece", language="en")
        assert [c.number for c in stored] == ["1190", "1189"], "newest first"
        assert stored[0].url == "https://example.test/1190"

    def test_recording_the_same_chapter_twice_is_not_new(self, db: Database) -> None:
        db.record_chapters("one-piece", [chapter("1190", 9)])
        assert db.record_chapters("one-piece", [chapter("1190", 9)]) == 0

    def test_only_genuinely_new_chapters_are_counted(self, db: Database) -> None:
        db.record_chapters("one-piece", [chapter("1189", 20)])
        assert db.record_chapters("one-piece", [chapter("1189", 20), chapter("1190", 9)]) == 1

    def test_languages_are_kept_apart(self, db: Database) -> None:
        db.record_chapters("one-piece", [chapter("1190", 9, "en"), chapter("1190", 9, "de")])
        assert len(db.chapters_for("one-piece", language="en")) == 1
        assert len(db.chapters_for("one-piece", language="de")) == 1

    def test_latest_chapter_is_the_newest_one(self, db: Database) -> None:
        db.record_chapters("one-piece", [chapter("1189", 20), chapter("1190", 9)])
        latest = db.latest_chapter("one-piece", language="en")
        assert latest is not None
        assert latest.number == "1190"

    def test_pruning_keeps_the_recent_tail(self, db: Database) -> None:
        db.record_chapters("x", [chapter(str(i), i) for i in range(1, 60)])
        db.prune_chapters(keep_per_series=10)
        remaining = db.chapters_for("x", language="en", limit=100)
        assert len(remaining) == 10
        assert remaining[0].number == "1", "the newest chapter survives pruning"

    def test_forgetting_a_series_removes_everything(self, db: Database) -> None:
        db.record_chapters("x", [chapter("1", 1)])
        db.save_learned("x", LearnedState(status=PublicationStatus.ONGOING))
        db.forget_series("x")
        assert db.chapters_for("x", language="en") == []
        assert db.load_learned("x").status is PublicationStatus.UNKNOWN


class TestLearnedState:
    def test_learned_state_round_trips(self, db: Database) -> None:
        state = LearnedState(
            status=PublicationStatus.HIATUS,
            cadence=Cadence(period=timedelta(days=7), weekday=6, hour=15, sample_size=8),
            breaks=[
                BreakWindow(
                    starts_at=NOW,
                    ends_at=NOW + timedelta(days=7),
                    reason="golden week",
                    confidence=Confidence.HIGH,
                )
            ],
            announced_next_at=NOW + timedelta(days=7),
        )
        db.save_learned("one-piece", state)
        loaded = db.load_learned("one-piece")

        assert loaded.status is PublicationStatus.HIATUS
        assert loaded.cadence.period == timedelta(days=7)
        assert loaded.cadence.weekday == 6
        assert loaded.breaks[0].reason == "golden week"
        assert loaded.announced_next_at == NOW + timedelta(days=7)

    def test_an_unknown_series_has_empty_state_rather_than_failing(self, db: Database) -> None:
        loaded = db.load_learned("never-seen")
        assert loaded.status is PublicationStatus.UNKNOWN
        assert loaded.breaks == []

    def test_saving_twice_overwrites(self, db: Database) -> None:
        db.save_learned("x", LearnedState(status=PublicationStatus.ONGOING))
        db.save_learned("x", LearnedState(status=PublicationStatus.COMPLETED))
        assert db.load_learned("x").status is PublicationStatus.COMPLETED


class TestPollState:
    def test_a_fresh_pair_is_due_immediately(self, db: Database) -> None:
        state = db.poll_state("one-piece", "mangadex")
        assert state.next_due_at is None, "never polled means owed right now"
        assert state.consecutive_errors == 0

    def test_poll_state_round_trips(self, db: Database) -> None:
        db.save_poll_state(
            PollState(
                series_key="one-piece",
                source_id="mangadex",
                next_due_at=NOW + timedelta(hours=6),
                consecutive_errors=2,
                etag='W/"abc"',
                watermark="chapter-1190",
                tier="near",
            )
        )
        state = db.poll_state("one-piece", "mangadex")
        assert state.next_due_at == NOW + timedelta(hours=6)
        assert state.consecutive_errors == 2
        assert state.etag == 'W/"abc"'
        assert state.watermark == "chapter-1190"
        assert state.tier == "near"

    def test_due_pairs_only_returns_what_is_actually_owed(self, db: Database) -> None:
        db.save_poll_state(
            PollState(series_key="a", source_id="mangadex", next_due_at=NOW - timedelta(minutes=1))
        )
        db.save_poll_state(
            PollState(series_key="b", source_id="mangadex", next_due_at=NOW + timedelta(hours=1))
        )
        assert db.due_pairs(NOW) == {("a", "mangadex")}

    def test_check_now_makes_everything_due(self, db: Database) -> None:
        db.save_poll_state(
            PollState(series_key="a", source_id="mangadex", next_due_at=NOW + timedelta(days=3))
        )
        db.clear_due()
        assert ("a", "mangadex") in db.due_pairs(NOW)

    def test_check_now_forgets_what_the_last_answer_was(self, db: Database) -> None:
        # Validators and watermarks answer the *previous* question, and the
        # reading language is part of that question. Keeping them would let a
        # source reply "nothing changed" right after a switch to German.
        db.save_poll_state(
            PollState(
                series_key="a",
                source_id="mangadex",
                next_due_at=NOW + timedelta(days=3),
                etag='W/"abc"',
                last_modified="Wed, 12 Aug 2026 10:00:00 GMT",
                watermark="2026-08-12T10:00:00+00:00",
            )
        )

        db.clear_due()

        state = db.poll_state("a", "mangadex")
        assert state.etag is None
        assert state.last_modified is None
        assert state.watermark is None


class TestReadState:
    def test_marking_read_records_the_chapter(self, db: Database) -> None:
        db.record_chapters("one-piece", [chapter("1190", 9)])
        db.mark_read("one-piece", db.latest_chapter("one-piece", language="en"))
        external_id, read_at = db.read_state("one-piece")
        assert external_id == "ch-1190-en"
        assert read_at is not None

    def test_nothing_read_yet_is_not_an_error(self, db: Database) -> None:
        assert db.read_state("one-piece") == (None, None)


class TestMigrations:
    def test_reopening_an_existing_database_keeps_the_data(self, tmp_path: Path) -> None:
        path = tmp_path / "mangame.db"
        with Database(path) as first:
            first.record_chapters("one-piece", [chapter("1190", 9)])
        with Database(path) as second:
            assert len(second.chapters_for("one-piece", language="en")) == 1


class TestSettings:
    def test_settings_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        settings = config_store.Settings(
            language="de",
            autostart=True,
            series=[
                config_store.SeriesConfig(
                    key="one-piece",
                    title="One Piece",
                    emblem="onepiece",
                    sources={"mangadex": "uuid-here"},
                )
            ],
        )
        config_store.save(settings, path)
        loaded = config_store.load(path)

        assert loaded.language == "de"
        assert loaded.autostart is True
        assert loaded.series[0].sources == {"mangadex": "uuid-here"}

    def test_a_missing_file_yields_usable_defaults(self, tmp_path: Path) -> None:
        loaded = config_store.load(tmp_path / "absent.json")
        assert loaded.language == "en"
        assert loaded.series == []

    def test_a_corrupt_file_does_not_stop_the_app_starting(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text("{not json at all", encoding="utf-8")
        assert config_store.load(path).series == []

    def test_saving_is_atomic(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        config_store.save(config_store.Settings(language="fr"), path)
        assert list(tmp_path.iterdir()) == [path], "no temp file left behind"

    def test_a_series_inherits_the_global_language_unless_overridden(self) -> None:
        settings = config_store.Settings(
            language="de",
            series=[
                config_store.SeriesConfig(key="a", title="A"),
                config_store.SeriesConfig(key="b", title="B", language="es"),
            ],
        )
        assert settings.language_for(settings.series[0]) == "de"
        assert settings.language_for(settings.series[1]) == "es"


class TestSeriesKey:
    """One title, one key — the add dialog and the store must agree on it."""

    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("One Piece", "one-piece"),
            ("ONE PIECE", "one-piece"),
            ("One Piece!", "one-piece"),
            ("  One Piece  ", "one-piece"),
            ("One Piece: Ace's Story", "one-piece-ace-s-story"),
            ("Kagurabachi", "kagurabachi"),
        ],
    )
    def test_a_title_becomes_a_slug(self, title: str, expected: str) -> None:
        assert config_store.series_key(title) == expected

    def test_a_title_with_nothing_sluggable_still_yields_a_key(self) -> None:
        # A key is a primary key; an empty one would collide with every other.
        assert config_store.series_key("!!!") == "series"
        assert config_store.series_key("") == "series"


class TestWhereThingsLive:
    """``MANGAME_HOME`` has to override on every platform, not just Linux.

    ``platformdirs`` reads the XDG variables on Linux and macOS but not on
    Windows. Isolation that leans on them passes locally and then writes into
    the real user profile on a Windows CI runner.
    """

    def test_the_home_variable_gathers_everything_in_one_place(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(paths.HOME_VAR, str(tmp_path / "portable"))

        assert paths.config_file().parent == tmp_path / "portable"
        assert paths.database_file().parent == tmp_path / "portable"
        assert paths.user_emblem_dir() == tmp_path / "portable" / "emblems"

    def test_the_directory_is_created_on_demand(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "not-yet"
        monkeypatch.setenv(paths.HOME_VAR, str(home))

        assert paths.config_dir().is_dir()
        assert home.is_dir()

    def test_a_tilde_is_expanded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A user typing the variable by hand will write ~/mangame.
        monkeypatch.setenv(paths.HOME_VAR, "~/mangame-test")

        override = paths.home_override()
        assert override is not None
        assert "~" not in str(override)
        assert override.is_absolute()

    def test_without_the_variable_the_platform_decides(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(paths.HOME_VAR, raising=False)

        assert paths.home_override() is None

    def test_an_empty_value_is_not_an_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Otherwise MANGAME_HOME= would resolve to the current directory.
        monkeypatch.setenv(paths.HOME_VAR, "")

        assert paths.home_override() is None

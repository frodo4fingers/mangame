"""Deriving the grey and break states from one picture.

These run without a display: every transform works on :class:`QImage`, which
needs no window system, so the pixel assertions here are the real thing rather
than a stand-in for it.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter

from mangame.domain.models import IconState
from mangame.ui import artwork, emblems

RED = "#E8352C"
YELLOW = "#F5D547"


def disc(path: Path, *, size: int = 128, fill: str = RED) -> Path:
    """A coloured circle on transparency, with a second colour inside it."""
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(fill))
    painter.drawEllipse(size // 8, size // 8, size * 3 // 4, size * 3 // 4)
    painter.setBrush(QColor(YELLOW))
    painter.drawEllipse(size * 3 // 8, size * 3 // 8, size // 4, size // 4)
    painter.end()

    image.save(str(path))
    return path


def flat(colour: str, size: int = 8) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor(colour))
    return image


def vector(path: Path) -> Path:
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<circle cx="32" cy="32" r="26" fill="#3B7DD8"/></svg>',
        encoding="utf-8",
    )
    return path


class TestLoading:
    @pytest.mark.parametrize("size", [16, 24, 64, 256])
    def test_a_raster_is_rendered_at_the_asked_for_size(self, tmp_path: Path, size: int) -> None:
        image = artwork.load(disc(tmp_path / "a.png"), size)
        assert (image.width(), image.height()) == (size, size)

    @pytest.mark.parametrize("size", [16, 24, 64, 256])
    def test_a_vector_is_rendered_at_the_asked_for_size(self, tmp_path: Path, size: int) -> None:
        # Rendered, not upscaled: a 64pt SVG asked for at 256 must be sharp.
        image = artwork.load(vector(tmp_path / "a.svg"), size)
        assert (image.width(), image.height()) == (size, size)

    def test_transparency_survives_loading(self, tmp_path: Path) -> None:
        image = artwork.load(disc(tmp_path / "a.png"), 64)
        assert image.pixelColor(0, 0).alpha() == 0
        assert image.pixelColor(32, 32).alpha() == 255

    def test_a_wide_picture_keeps_its_proportions(self, tmp_path: Path) -> None:
        wide = QImage(200, 50, QImage.Format.Format_ARGB32)
        wide.fill(QColor(RED))
        path = tmp_path / "wide.png"
        wide.save(str(path))

        image = artwork.load(path, 64)
        # Squashing to a square would fill the whole canvas; letterboxing
        # leaves the top and bottom clear and centres the picture.
        assert image.pixelColor(32, 2).alpha() == 0
        assert image.pixelColor(32, 32).alpha() == 255

    def test_an_unknown_extension_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_text("not a picture", encoding="utf-8")
        with pytest.raises(artwork.UnsupportedArtworkError):
            artwork.load(path, 32)

    def test_a_corrupt_image_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.png"
        path.write_bytes(b"\x89PNG\r\n\x1a\n garbage")
        with pytest.raises(artwork.UnsupportedArtworkError):
            artwork.load(path, 32)

    def test_a_corrupt_vector_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.svg"
        path.write_text("<svg", encoding="utf-8")
        with pytest.raises(artwork.UnsupportedArtworkError):
            artwork.load(path, 32)


class TestGrayscale:
    def test_every_pixel_loses_its_colour(self, tmp_path: Path) -> None:
        grey = artwork.grayscale(artwork.load(disc(tmp_path / "a.png"), 64))
        for y in range(0, 64, 7):
            for x in range(0, 64, 7):
                pixel = grey.pixelColor(x, y)
                assert pixel.red() == pixel.green() == pixel.blue()

    def test_transparency_is_kept(self, tmp_path: Path) -> None:
        grey = artwork.grayscale(artwork.load(disc(tmp_path / "a.png"), 64))
        assert grey.pixelColor(0, 0).alpha() == 0
        assert grey.pixelColor(32, 32).alpha() == 255

    def test_black_and_white_are_pulled_into_the_mid_band(self) -> None:
        darkest = artwork.grayscale(flat("#000000")).pixelColor(4, 4).red()
        lightest = artwork.grayscale(flat("#FFFFFF")).pixelColor(4, 4).red()
        assert darkest == pytest.approx(artwork.GREY_FLOOR * 255, abs=2)
        assert lightest == pytest.approx(artwork.GREY_CEILING * 255, abs=2)

    def test_dark_artwork_does_not_come_out_looking_like_a_break(self) -> None:
        # The whole reason for the band: plain luminance would render dark
        # artwork near-black, which is exactly what "on break" looks like.
        grey = artwork.grayscale(flat("#101010")).pixelColor(4, 4).red()
        silhouette_fill = QColor(artwork.BREAK_FILL).red()
        assert grey - silhouette_fill > 50

    def test_brighter_input_stays_brighter(self) -> None:
        shades = ("#222222", "#888888", "#EEEEEE")
        levels = [artwork.grayscale(flat(shade)).pixelColor(4, 4).red() for shade in shades]
        assert levels == sorted(levels)

    def test_green_reads_lighter_than_blue(self) -> None:
        # Luminance, not a channel average: human vision weights green most.
        green = artwork.grayscale(flat("#00FF00")).pixelColor(4, 4).red()
        blue = artwork.grayscale(flat("#0000FF")).pixelColor(4, 4).red()
        assert green > blue


class TestSilhouette:
    def test_the_body_is_flattened_to_near_black(self, tmp_path: Path) -> None:
        image = artwork.load(disc(tmp_path / "a.png"), 64)
        result = artwork.silhouette(artwork._inset(image, 2))
        expected = QColor(artwork.BREAK_FILL).name()
        # The two source colours must have become the same one.
        assert result.pixelColor(32, 32).name() == expected
        assert result.pixelColor(32, 22).name() == expected

    def test_the_shape_is_ringed_in_near_white(self, tmp_path: Path) -> None:
        # Without this rim a dark silhouette vanishes on a dark panel.
        image = artwork.load(disc(tmp_path / "a.png"), 64)
        result = artwork.silhouette(artwork._inset(image, 2))

        row = [result.pixelColor(x, 32) for x in range(64)]
        first = next(x for x, pixel in enumerate(row) if pixel.alpha() > 200)
        assert row[first].name() == QColor(artwork.BREAK_RIM).name()
        assert row[32].name() == QColor(artwork.BREAK_FILL).name()

    def test_the_rim_never_runs_off_the_canvas(self, tmp_path: Path) -> None:
        # A picture drawn edge to edge still has to fit its halo, so
        # ``state_image`` insets by exactly the rim it is about to grow.
        edge = QImage(64, 64, QImage.Format.Format_ARGB32)
        edge.fill(QColor(RED))
        path = tmp_path / "full.png"
        edge.save(str(path))

        result = artwork.state_image(path, IconState.BREAK, 64)
        rim = QColor(artwork.BREAK_RIM).name()
        assert result.pixelColor(0, 32).name() == rim
        assert result.pixelColor(63, 32).name() == rim

    @pytest.mark.parametrize(("size", "expected"), [(16, 1), (24, 1), (64, 2), (256, 8)])
    def test_the_rim_grows_with_the_icon(self, size: int, expected: int) -> None:
        assert artwork.rim_width(size) == expected


class TestStateImage:
    def test_ready_keeps_the_original_colours(self, tmp_path: Path) -> None:
        image = artwork.state_image(disc(tmp_path / "a.png"), IconState.READY, 64)
        assert image.pixelColor(32, 20).name() == QColor(RED).name()

    def test_due_is_grey(self, tmp_path: Path) -> None:
        pixel = artwork.state_image(disc(tmp_path / "a.png"), IconState.DUE, 64).pixelColor(32, 20)
        assert pixel.red() == pixel.green() == pixel.blue()

    def test_break_is_a_silhouette(self, tmp_path: Path) -> None:
        image = artwork.state_image(disc(tmp_path / "a.png"), IconState.BREAK, 64)
        assert image.pixelColor(32, 32).name() == QColor("#232323").name()

    def test_the_three_states_are_told_apart_at_tray_size(self, tmp_path: Path) -> None:
        # The reason the whole module exists. At 16px there is no detail left
        # to read, so the states have to differ in overall brightness.
        source = disc(tmp_path / "a.png")

        def brightness(state: IconState) -> float:
            image = artwork.state_image(source, state, 16)
            pixels = [image.pixelColor(x, y) for x in range(16) for y in range(16)]
            opaque = [p for p in pixels if p.alpha() > 128]
            return sum(p.lightness() for p in opaque) / len(opaque)

        ready, due, on_break = (brightness(state) for state in IconState)
        assert on_break < due
        assert abs(due - on_break) > 40
        assert abs(ready - on_break) > 20


class TestNaming:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("One Piece", "one-piece"),
            ("  Spy × Family  ", "spy-family"),  # noqa: RUF001 - the real title
            ("Kagurabachi!", "kagurabachi"),
            ("JUJUTSU_KAISEN", "jujutsu-kaisen"),
            ("chainsaw--man", "chainsaw-man"),
            ("僕のヒーロー", "僕のヒーロー"),
            ("   ", ""),
            ("!!!", ""),
        ],
    )
    def test_names_fold_to_something_a_directory_can_hold(self, raw: str, expected: str) -> None:
        assert artwork.emblem_name(raw) == expected


class TestInstalling:
    def test_one_source_and_one_file_per_state_are_written(
        self, tmp_path: Path, emblem_home: Path
    ) -> None:
        name = artwork.install(disc(tmp_path / "a.png"), "My Hat")

        assert name == "my-hat"
        assert (emblem_home / "my-hat.png").is_file()
        for state in IconState:
            image = QImage(str(emblem_home / name / f"{state.value}.png"))
            assert image.size().width() == artwork.OUTPUT_SIZE
            assert image.size().height() == artwork.OUTPUT_SIZE

    def test_an_installed_emblem_becomes_selectable(
        self, tmp_path: Path, emblem_home: Path
    ) -> None:
        assert "my-hat" not in emblems.selectable_emblems()
        artwork.install(disc(tmp_path / "a.png"), "My Hat")
        assert "my-hat" in emblems.selectable_emblems()
        assert artwork.user_emblems() == ["my-hat"]

    def test_the_icon_cache_is_dropped_so_new_artwork_shows_at_once(
        self, tmp_path: Path, emblem_home: Path, qapp: object
    ) -> None:
        # icon_for is memoised; without the invalidation an import would not
        # appear in the tray until a restart. The monogram it starts out
        # returning is drawn with QPixmap, hence the application fixture.
        before = emblems.icon_for("my-hat", IconState.READY, "Series")
        artwork.install(disc(tmp_path / "a.png"), "My Hat")
        after = emblems.icon_for("my-hat", IconState.READY, "Series")
        assert before is not after

    def test_a_vector_can_be_installed(self, tmp_path: Path, emblem_home: Path) -> None:
        artwork.install(vector(tmp_path / "a.svg"), "vector-hat")
        assert (emblem_home / "vector-hat.png").exists()
        assert (emblem_home / "vector-hat" / "ready.png").exists()

    def test_an_unnamed_emblem_is_refused(self, tmp_path: Path, emblem_home: Path) -> None:
        with pytest.raises(artwork.UnsupportedArtworkError):
            artwork.install(disc(tmp_path / "a.png"), "   ")

    def test_installing_the_same_name_twice_replaces_it(
        self, tmp_path: Path, emblem_home: Path
    ) -> None:
        artwork.install(disc(tmp_path / "red.png", fill=RED), "hat")
        artwork.install(disc(tmp_path / "blue.png", fill="#3B7DD8"), "hat")

        ready = QImage(str(emblem_home / "hat" / "ready.png"))
        assert ready.pixelColor(128, 80).name() == QColor("#3B7DD8").name()
        assert artwork.user_emblems() == ["hat"]


class TestDroppedPNGs:
    def test_a_png_dropped_at_the_root_is_generated(self, emblem_home: Path) -> None:
        disc(emblem_home / "Hunter x Hunter.png")

        assert artwork.sync_dropins() == ["hunter-x-hunter"]
        for state in IconState:
            assert (emblem_home / "hunter-x-hunter" / f"{state.value}.png").is_file()

    @pytest.mark.parametrize(
        ("title", "folder"),
        [("Hunter x Hunter", "hunter-x-hunter"), ("僕のヒーロー", "僕のヒーロー")],
    )
    def test_a_matching_drop_in_overrides_the_generated_monogram(
        self, emblem_home: Path, qapp: object, title: str, folder: str
    ) -> None:
        disc(emblem_home / f"{title}.png")
        artwork.sync_dropins()

        shown = emblems.icon_for("monogram", IconState.READY, title)
        expected = QIcon(str(emblem_home / folder / "ready.png"))

        assert bytes(shown.pixmap(22, 22).toImage().constBits()) == bytes(
            expected.pixmap(22, 22).toImage().constBits()
        )

    def test_an_unchanged_drop_in_is_not_rendered_again(self, emblem_home: Path) -> None:
        disc(emblem_home / "a.png")
        artwork.sync_dropins()
        target = emblem_home / "a" / "ready.png"
        written = target.stat().st_mtime_ns

        assert artwork.sync_dropins() == []
        assert target.stat().st_mtime_ns == written

    def test_changing_the_source_regenerates_the_states(self, emblem_home: Path) -> None:
        source = disc(emblem_home / "a.png", fill=RED)
        artwork.sync_dropins()
        before = QImage(str(emblem_home / "a" / "ready.png")).pixelColor(128, 80)

        disc(source, fill="#3B7DD8")
        assert artwork.sync_dropins() == ["a"]
        after = QImage(str(emblem_home / "a" / "ready.png")).pixelColor(128, 80)

        assert before != after

    def test_a_broken_drop_in_is_logged_and_skipped(
        self, emblem_home: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        (emblem_home / "broken.png").write_bytes(b"not an image")

        assert artwork.sync_dropins() == []
        assert not (emblem_home / "broken").exists()
        assert "could not generate emblem" in caplog.text

    def test_a_broken_replacement_keeps_the_last_working_states(self, emblem_home: Path) -> None:
        source = disc(emblem_home / "a.png")
        artwork.sync_dropins()
        target = emblem_home / "a" / "ready.png"
        working = target.read_bytes()

        source.write_bytes(b"not an image")

        assert artwork.sync_dropins() == []
        assert target.read_bytes() == working


class TestUninstalling:
    def test_an_installed_emblem_can_be_dropped(self, tmp_path: Path, emblem_home: Path) -> None:
        artwork.install(disc(tmp_path / "a.png"), "hat")
        assert artwork.uninstall("hat") is True
        assert artwork.user_emblems() == []
        assert not (emblem_home / "hat").exists()
        assert not (emblem_home / "hat.png").exists()

    def test_dropping_something_that_was_never_there_is_harmless(self, emblem_home: Path) -> None:
        assert artwork.uninstall("nothing") is False

    def test_bundled_artwork_is_out_of_reach(self, emblem_home: Path) -> None:
        # "book" ships with the app; uninstall only ever looks in the user
        # directory, so asking for it must not delete anything.
        assert artwork.uninstall("book") is False
        assert (emblems.BUNDLED_DIR / "book").is_dir()
        assert "book" in emblems.available_emblems()

"""Deriving the grey and break states from one picture.

These run without a display: every transform works on :class:`QImage`, which
needs no window system, so the pixel assertions here are the real thing rather
than a stand-in for it.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter

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
        silhouette_fill = QColor(artwork.TONES[artwork.SilhouetteTone.DARK][0]).red()
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
    @pytest.mark.parametrize("tone", list(artwork.SilhouetteTone))
    def test_the_body_is_flattened_to_one_tone(
        self, tmp_path: Path, tone: artwork.SilhouetteTone
    ) -> None:
        image = artwork.load(disc(tmp_path / "a.png"), 64)
        result = artwork.silhouette(artwork._inset(image, 2), tone)
        expected = QColor(artwork.TONES[tone][0]).name()
        # The two source colours must have become the same one.
        assert result.pixelColor(32, 32).name() == expected
        assert result.pixelColor(32, 22).name() == expected

    @pytest.mark.parametrize("tone", list(artwork.SilhouetteTone))
    def test_the_shape_is_ringed_in_the_contrasting_tone(
        self, tmp_path: Path, tone: artwork.SilhouetteTone
    ) -> None:
        # Without this rim a dark silhouette vanishes on a dark panel.
        image = artwork.load(disc(tmp_path / "a.png"), 64)
        result = artwork.silhouette(artwork._inset(image, 2), tone)

        row = [result.pixelColor(x, 32) for x in range(64)]
        first = next(x for x, pixel in enumerate(row) if pixel.alpha() > 200)
        assert row[first].name() == QColor(artwork.TONES[tone][1]).name()
        assert row[32].name() == QColor(artwork.TONES[tone][0]).name()

    def test_the_two_tones_are_opposites(self) -> None:
        dark_fill, dark_rim = artwork.TONES[artwork.SilhouetteTone.DARK]
        light_fill, light_rim = artwork.TONES[artwork.SilhouetteTone.LIGHT]
        assert QColor(dark_fill).lightness() < QColor(dark_rim).lightness()
        assert QColor(light_fill).lightness() > QColor(light_rim).lightness()

    def test_the_rim_never_runs_off_the_canvas(self, tmp_path: Path) -> None:
        # A picture drawn edge to edge still has to fit its halo, so
        # ``state_image`` insets by exactly the rim it is about to grow.
        edge = QImage(64, 64, QImage.Format.Format_ARGB32)
        edge.fill(QColor(RED))
        path = tmp_path / "full.png"
        edge.save(str(path))

        result = artwork.state_image(path, IconState.BREAK, 64)
        rim = QColor(artwork.TONES[artwork.SilhouetteTone.DARK][1]).name()
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
    def test_every_state_and_size_is_written(self, tmp_path: Path, emblem_home: Path) -> None:
        name = artwork.install(disc(tmp_path / "a.png"), "My Hat")

        assert name == "my-hat"
        for state in IconState:
            written = {int(p.stem) for p in (emblem_home / name / state.value).glob("*.png")}
            assert set(emblems.SIZES) <= written

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
        assert (emblem_home / "vector-hat" / "ready" / "64.png").exists()

    def test_an_unnamed_emblem_is_refused(self, tmp_path: Path, emblem_home: Path) -> None:
        with pytest.raises(artwork.UnsupportedArtworkError):
            artwork.install(disc(tmp_path / "a.png"), "   ")

    def test_installing_the_same_name_twice_replaces_it(
        self, tmp_path: Path, emblem_home: Path
    ) -> None:
        artwork.install(disc(tmp_path / "red.png", fill=RED), "hat")
        artwork.install(disc(tmp_path / "blue.png", fill="#3B7DD8"), "hat")

        ready = QImage(str(emblem_home / "hat" / "ready" / "64.png"))
        assert ready.pixelColor(32, 20).name() == QColor("#3B7DD8").name()
        assert artwork.user_emblems() == ["hat"]

    def test_the_break_tone_is_honoured(self, tmp_path: Path, emblem_home: Path) -> None:
        artwork.install(disc(tmp_path / "a.png"), "pale", artwork.SilhouetteTone.LIGHT)
        image = QImage(str(emblem_home / "pale" / "break" / "64.png"))
        assert image.pixelColor(32, 32).name() == QColor("#EDEDED").name()


class TestUninstalling:
    def test_an_installed_emblem_can_be_dropped(self, tmp_path: Path, emblem_home: Path) -> None:
        artwork.install(disc(tmp_path / "a.png"), "hat")
        assert artwork.uninstall("hat") is True
        assert artwork.user_emblems() == []
        assert not (emblem_home / "hat").exists()

    def test_dropping_something_that_was_never_there_is_harmless(self, emblem_home: Path) -> None:
        assert artwork.uninstall("nothing") is False

    def test_bundled_artwork_is_out_of_reach(self, emblem_home: Path) -> None:
        # "book" ships with the app; uninstall only ever looks in the user
        # directory, so asking for it must not delete anything.
        assert artwork.uninstall("book") is False
        assert (emblems.BUNDLED_DIR / "book").is_dir()
        assert "book" in emblems.available_emblems()

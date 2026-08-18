"""The generic RSS/Atom adapter — how a new site becomes a config line."""

from datetime import UTC, datetime

import pytest

from mangame.sources.base import SourceError
from mangame.sources.feed import chapter_number, parse_feed

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example scans</title>
    <item>
      <title>Kagurabachi Chapter 128</title>
      <link>https://example.test/kagurabachi/128</link>
      <guid>https://example.test/kagurabachi/128</guid>
      <pubDate>Sun, 09 Aug 2026 15:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Kagurabachi Chapter 127</title>
      <link>https://example.test/kagurabachi/127</link>
      <guid>https://example.test/kagurabachi/127</guid>
      <pubDate>Sun, 02 Aug 2026 15:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example</title>
  <entry>
    <title>Vagabond, Ch. 300</title>
    <id>tag:example.test,2026:300</id>
    <link href="https://example.test/vagabond/300"/>
    <published>2026-08-09T15:00:00Z</published>
  </entry>
  <entry>
    <title>Vagabond, Ch. 299</title>
    <id>tag:example.test,2026:299</id>
    <link href="https://example.test/vagabond/299"/>
    <updated>2026-08-02T15:00:00Z</updated>
  </entry>
</feed>
"""


class TestChapterNumber:
    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Kagurabachi Chapter 128", "128"),
            ("Chapter #45", "45"),
            ("One Piece Ch. 1190", "1190"),
            ("Ch 12.5 - omake", "12.5"),
            ("Some Manga #77", "77"),
            ("Episode 9", "9"),
            ("Blue Lock 301", "301"),
            ("A title with no number at all", None),
        ],
    )
    def test_extraction(self, title: str, expected: str | None) -> None:
        assert chapter_number(title) == expected

    def test_explicit_wording_beats_a_trailing_number(self) -> None:
        assert chapter_number("Volume 3 Chapter 128") == "128"


class TestParseFeed:
    def test_rss_items_become_chapters(self) -> None:
        chapters = parse_feed(RSS, source_id="feed", language="en")
        assert [c.number for c in chapters] == ["128", "127"]
        assert chapters[0].published_at == datetime(2026, 8, 9, 15, 0, tzinfo=UTC)
        assert chapters[0].url == "https://example.test/kagurabachi/128"
        assert chapters[0].external_id == "https://example.test/kagurabachi/128"

    def test_atom_entries_become_chapters(self) -> None:
        chapters = parse_feed(ATOM, source_id="feed", language="en")
        assert [c.number for c in chapters] == ["300", "299"]
        assert chapters[0].url == "https://example.test/vagabond/300"

    def test_atom_falls_back_from_published_to_updated(self) -> None:
        chapters = parse_feed(ATOM, source_id="feed", language="en")
        assert chapters[1].published_at == datetime(2026, 8, 2, 15, 0, tzinfo=UTC)

    def test_items_without_a_date_are_useless_and_skipped(self) -> None:
        undated = """<rss version="2.0"><channel>
          <item><title>Chapter 5</title></item>
          <item><title>Chapter 4</title><pubDate>Sun, 02 Aug 2026 15:00:00 +0000</pubDate></item>
        </channel></rss>"""
        chapters = parse_feed(undated, source_id="feed", language="en")
        assert [c.number for c in chapters] == ["4"]

    def test_items_without_a_guid_still_get_a_stable_identifier(self) -> None:
        anonymous = """<rss version="2.0"><channel>
          <item><title>Chapter 4</title><pubDate>Sun, 02 Aug 2026 15:00:00 +0000</pubDate></item>
        </channel></rss>"""
        first = parse_feed(anonymous, source_id="feed", language="en")
        second = parse_feed(anonymous, source_id="feed", language="en")
        assert first[0].external_id == second[0].external_id

    def test_the_configured_language_is_carried_through(self) -> None:
        assert parse_feed(RSS, source_id="feed", language="de")[0].language == "de"

    def test_broken_xml_is_a_source_error_not_a_crash(self) -> None:
        with pytest.raises(SourceError):
            parse_feed("<rss><channel><item>", source_id="feed", language="en")

    def test_an_unrecognised_dialect_yields_nothing(self) -> None:
        assert parse_feed("<html><body>nope</body></html>", source_id="feed", language="en") == []

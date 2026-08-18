"""Generic RSS/Atom adapter — the escape hatch.

This is the answer to "check a huge variety of sources with minimal effort".
Writing a bespoke adapter per site does not scale; almost every manga site,
aggregator, tracker and publisher blog already emits a feed, and a feed carries
exactly the two things :mod:`mangame.domain` needs — item titles and
publication timestamps.

So the ``ref`` for this source *is* the feed URL. Adding a new site is a config
line, not a release. Feeds also honour ``ETag``/``If-Modified-Since`` properly,
which makes the tight hot-window polling nearly free.

Because the URL is one the user chose deliberately, whatever it publishes is
taken to be in the language they are reading — that is how a reader adds a
German or Spanish scanlation site that no global index can attribute. This is
the opposite of an index we merely query, which must never guess a language.
"""

import re
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree

from mangame.domain.models import Chapter, SourceSignal
from mangame.i18n import languages
from mangame.sources.base import Capabilities, FetchRequest, SourceError, SourceMatch
from mangame.sources.http import HttpClient

ATOM_NS = "{http://www.w3.org/2005/Atom}"

#: Ordered from most to least explicit; first match wins.
_CHAPTER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"chapter\s*#?\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bch\.?\s*#?\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bepisode\s*#?\s*(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"#\s*(\d+(?:\.\d+)?)"),
    re.compile(r"(\d+(?:\.\d+)?)\s*$"),
)


def chapter_number(title: str) -> str | None:
    """Best-effort chapter number from a free-form feed item title."""
    for pattern in _CHAPTER_PATTERNS:
        match = pattern.search(title)
        if match:
            return match.group(1)
    return None


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text).astimezone(UTC)
    except (TypeError, ValueError):
        return None


def _text(node: Any, *names: str) -> str | None:
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return str(found.text).strip()
    return None


def _link(node: Any) -> str | None:
    plain = _text(node, "link")
    if plain:
        return plain
    atom_link = node.find(f"{ATOM_NS}link")
    if atom_link is not None:
        href = atom_link.get("href")
        return str(href) if href else None
    return None


def parse_feed(xml_text: str, *, source_id: str, language: str) -> list[Chapter]:
    """Parse RSS 2.0 or Atom into chapters. Unknown dialects yield nothing."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise SourceError(f"unparseable feed: {exc}") from exc

    entries = root.findall(".//item") or root.findall(f".//{ATOM_NS}entry")
    chapters: list[Chapter] = []

    for index, entry in enumerate(entries):
        title = _text(entry, "title", f"{ATOM_NS}title") or ""
        published = _parse_datetime(
            _text(
                entry,
                "pubDate",
                "published",
                f"{ATOM_NS}published",
                f"{ATOM_NS}updated",
                "{http://purl.org/dc/elements/1.1/}date",
            )
        )
        if published is None:
            continue
        identifier = (
            _text(entry, "guid", "id", f"{ATOM_NS}id") or f"{published.isoformat()}#{index}"
        )
        chapters.append(
            Chapter(
                source_id=source_id,
                external_id=identifier,
                number=chapter_number(title),
                title=title or None,
                language=language,
                published_at=published,
                url=_link(entry),
            )
        )
    return chapters


class FeedSource:
    """Any RSS/Atom URL becomes a source. ``ref`` is the feed URL itself."""

    source_id = "feed"
    display_name = "RSS / Atom feed"
    capabilities = Capabilities(
        chapter_timestamps=True,
        announced_next_date=False,
        hiatus_flag=False,
        search=False,
        batch_feed=False,
        languages=frozenset(languages.codes()),
    )
    min_interval = timedelta(minutes=10)

    async def search(self, client: HttpClient, query: str, *, limit: int = 10) -> list[SourceMatch]:
        """Feeds are not searchable; the user supplies the URL directly."""
        return []

    async def fetch(self, client: HttpClient, request: FetchRequest) -> SourceSignal:
        now = datetime.now(UTC)
        response = await client.get_json(
            request.ref,
            validators=request.validators,
            parse_json=False,
            headers={"Accept": "application/rss+xml, application/atom+xml, */*"},
        )
        if response.not_modified:
            return SourceSignal(
                source_id=self.source_id,
                fetched_at=now,
                etag=request.validators.etag,
                last_modified=request.validators.last_modified,
                watermark=request.watermark,
                unchanged=True,
            )

        chapters = parse_feed(
            str(response.payload or ""),
            source_id=self.source_id,
            language=request.language,
        )
        newest = max(chapters, key=lambda c: c.published_at, default=None)
        return SourceSignal(
            source_id=self.source_id,
            fetched_at=now,
            chapters=chapters,
            etag=response.validators.etag,
            last_modified=response.validators.last_modified,
            watermark=newest.external_id if newest else None,
        )

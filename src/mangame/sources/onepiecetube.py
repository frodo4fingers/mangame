"""OnePiece-Tube — a German fan translation that runs ahead of the simulpub.

The official sources are the truth about *scheduling*: MANGA Plus announces the
next chapter's date, and mangame trusts that announcement over its own guess.
But they are not the truth about *availability*. A German scanlation is
routinely readable days before the licensed release, and a tracker that only
ever asks the publisher will keep showing "expected Sunday" while the chapter
sits on a reader's screen.

This adapter closes that gap for the one series the site carries. It is not
generic and does not pretend to be — the value here is the site's list page,
which ships its whole catalogue as JSON in a ``window.__data`` assignment.
That gives real chapter numbers, availability flags and dates without parsing
a single element of markup, and it makes ``ref`` a page to read rather than a
series id to look up.

Two properties of that data shape the adapter:

* Older entries are listed but not hosted (``is_available`` false, zero pages).
  Reporting those would turn the icon "ready" for chapters that cannot be
  opened, so only entries the site can actually serve are returned.
* Dates carry no time of day. See :data:`DAY_START` for what is done about it.
"""

import json
import re
from datetime import UTC, date, datetime, time, timedelta

from mangame.domain.models import Chapter, SourceSignal
from mangame.sources.base import Capabilities, FetchRequest, SourceError, SourceMatch
from mangame.sources.http import HttpClient

SITE = "https://onepiece.tube"

#: The catalogue page. Also the default ``ref``, so tracking needs no id.
LIST_URL = f"{SITE}/manga/kapitel-mangaliste"

#: The only series and the only language this site carries.
SERIES_TITLE = "One Piece"
LANGUAGE = "de"
SITE_LANGUAGE = "ger"

#: Polite for a small fan site with no CDN in front of it. The poll ladder can
#: ask for ten-minute intervals in the hot window; this is the floor it hits.
RATE_PER_SECOND = 0.5
MIN_INTERVAL = timedelta(minutes=30)

#: How many recent chapters to report. Cadence needs a handful of intervals,
#: and the whole catalogue is over a thousand entries of 2006-era history.
CHAPTER_LIMIT = 24

#: Dates arrive as ``DD.MM.YYYY`` with no time, so one has to be chosen.
#: The start of the day is the only choice that cannot invent a release in the
#: future: a chapter published this morning would otherwise carry a timestamp
#: hours ahead of now, and adapters here drop future-dated chapters because a
#: scheduled chapter is not a released one. The cost is that a date-only source
#: teaches midnight as the publishing hour when nothing more precise is known.
DAY_START = time(0, 0, tzinfo=UTC)

_DATA = re.compile(r"window\.__data\s*=\s*")
_DATE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")


def _payload(html: str) -> dict[str, object]:
    """Pull the embedded catalogue out of the page's ``window.__data``."""
    match = _DATA.search(html)
    if match is None:
        raise SourceError("no window.__data payload on the chapter list page")
    try:
        # The assignment is followed by the rest of the script, so decode just
        # the object that starts here rather than trying to find where it ends.
        data, _end = json.JSONDecoder().raw_decode(html, match.end())
    except ValueError as exc:
        raise SourceError(f"unparseable window.__data payload: {exc}") from exc
    if not isinstance(data, dict):
        raise SourceError("window.__data is not an object")
    return data


def _published_at(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    match = _DATE.match(raw.strip())
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return datetime.combine(date(year, month, day), DAY_START)
    except ValueError:
        return None


def _number(raw: object) -> str | None:
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        return None
    return str(int(raw)) if float(raw).is_integer() else str(raw)


def _is_readable(entry: dict[str, object]) -> bool:
    """Can this entry actually be opened, or is it catalogue filler?

    The site lists every chapter ever published but hosts only some of them.
    An entry it cannot serve is history, not a release.
    """
    pages = entry.get("pages")
    has_pages = isinstance(pages, int) and not isinstance(pages, bool) and pages > 0
    return entry.get("is_available") is True and has_pages


def parse_chapter_list(html: str, *, limit: int = CHAPTER_LIMIT) -> list[Chapter]:
    """Chapters from the catalogue page, newest first, readable ones only."""
    entries = _payload(html).get("entries")
    if not isinstance(entries, list):
        raise SourceError("window.__data carries no entries list")

    chapters: list[Chapter] = []
    for entry in entries:
        if not isinstance(entry, dict) or not _is_readable(entry):
            continue
        if entry.get("lang") not in (SITE_LANGUAGE, None):
            continue
        published_at = _published_at(entry.get("date"))
        number = _number(entry.get("number"))
        if published_at is None or number is None:
            continue

        identifier = entry.get("id")
        url = entry.get("href")
        chapters.append(
            Chapter(
                source_id=OnePieceTubeSource.source_id,
                external_id=str(identifier) if identifier is not None else f"ch-{number}",
                number=number,
                title=entry.get("name") if isinstance(entry.get("name"), str) else None,
                language=LANGUAGE,
                published_at=published_at,
                url=url if isinstance(url, str) else None,
            )
        )
        if len(chapters) >= limit:
            break
    return chapters


def _wants_one_piece(query: str) -> bool:
    """Does this search plausibly mean the only series the site carries?

    Matching anything would put One Piece in the results for "Naruto", so the
    title has to be recognisable once punctuation and spacing are ignored.
    """
    condensed = re.sub(r"[^a-z0-9]+", "", query.casefold())
    return not condensed or "onepiece" in condensed


class OnePieceTubeSource:
    """The German OnePiece-Tube catalogue. ``ref`` is the list page URL."""

    source_id = "onepiecetube"
    display_name = "OnePiece-Tube (German scanlation)"
    capabilities = Capabilities(
        chapter_timestamps=True,
        announced_next_date=False,
        hiatus_flag=False,
        search=True,
        batch_feed=False,
        languages=frozenset({LANGUAGE}),
    )
    min_interval = MIN_INTERVAL

    def __init__(self, *, chapter_limit: int = CHAPTER_LIMIT) -> None:
        self._chapter_limit = chapter_limit

    async def search(
        self,
        client: HttpClient,
        query: str,
        *,
        language: str = "en",
        limit: int = 10,
    ) -> list[SourceMatch]:
        """One site, one series — so this is a name check, not a request."""
        del client, limit
        if language != LANGUAGE or not _wants_one_piece(query):
            return []
        return [
            SourceMatch(
                source_id=self.source_id,
                ref=LIST_URL,
                title=SERIES_TITLE,
                url=LIST_URL,
                year=1997,
                hint="German fan translation, usually ahead of the official release",
            )
        ]

    async def fetch(self, client: HttpClient, request: FetchRequest) -> SourceSignal:
        now = datetime.now(UTC)
        response = await client.get_json(
            request.ref or LIST_URL,
            validators=request.validators,
            parse_json=False,
            headers={"Accept": "text/html,application/xhtml+xml"},
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

        chapters = parse_chapter_list(str(response.payload or ""), limit=self._chapter_limit)
        # A chapter dated later today is not out yet; the site fills the date in
        # when it schedules the entry, not when the pages go up.
        chapters = [c for c in chapters if c.published_at <= now]
        newest = max(chapters, key=lambda c: c.published_at, default=None)

        return SourceSignal(
            source_id=self.source_id,
            fetched_at=now,
            chapters=chapters,
            etag=response.validators.etag,
            last_modified=response.validators.last_modified,
            watermark=newest.external_id if newest else None,
        )

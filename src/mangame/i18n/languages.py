"""The languages mangame can actually read manga in.

This is the *reading* language: the language of the chapters you want, which is
what decides which sources get polled and which chapters count as "ready". It
is not merely a UI preference — a German reader is waiting for the German
release, and an English chapter appearing does not make the icon go colour.

Two facts from the sources shape this module:

* A language is not one code. MangaDex splits Spanish into ``es`` (Spain) and
  ``es-la`` (Latin America), and a reader who asked for Spanish wants both.
  Every canonical language therefore carries the family of codes to ask for,
  and whatever comes back is folded onto the canonical code so that one stored
  language means one thing.
* Not every source can attribute a language at all (see
  :class:`~mangame.sources.base.Capabilities`), which is why the canonical set
  is kept deliberately small and explicit rather than "whatever the API lists".
"""

from typing import Final

from pydantic import BaseModel, ConfigDict


class Language(BaseModel):
    """One language mangame can read in."""

    model_config = ConfigDict(frozen=True)

    code: str
    """Canonical code, stored in settings and against every chapter."""

    label: str
    """Native name, shown in the menu."""

    source_codes: tuple[str, ...]
    """Every code a source may use for this language, the canonical one first."""


SUPPORTED: Final[tuple[Language, ...]] = (
    Language(code="en", label="English", source_codes=("en",)),
    Language(code="es", label="Español", source_codes=("es", "es-la")),
    Language(code="de", label="Deutsch", source_codes=("de",)),
)

DEFAULT: Final[str] = "en"

_BY_CODE: Final[dict[str, Language]] = {language.code: language for language in SUPPORTED}
_CANONICAL: Final[dict[str, str]] = {
    source_code: language.code for language in SUPPORTED for source_code in language.source_codes
}


def codes() -> tuple[str, ...]:
    return tuple(_BY_CODE)


def labels() -> dict[str, str]:
    """``{code: native name}``, in menu order."""
    return {language.code: language.label for language in SUPPORTED}


def normalize(tag: str) -> str:
    """Fold any language tag onto a supported reading language.

    Accepts what settings files, operating systems and APIs actually contain:
    ``pt-BR``, ``de_DE.UTF-8``, ``ES``, ``es-419``. Anything unsupported
    degrades to :data:`DEFAULT` rather than leaving the app with a language no
    source can serve.
    """
    cleaned = tag.strip().lower().replace("_", "-").split(".")[0]
    if cleaned in _CANONICAL:
        return _CANONICAL[cleaned]
    base = cleaned.split("-")[0]
    return _CANONICAL.get(base, DEFAULT)


def get(code: str) -> Language:
    """The language record for ``code``, falling back to :data:`DEFAULT`."""
    return _BY_CODE[normalize(code)]


def source_codes(code: str) -> tuple[str, ...]:
    """Every code to ask a source for when the user wants ``code``."""
    return get(code).source_codes


def canonical(source_code: str) -> str:
    """Fold a code a source reported back onto its canonical language."""
    return normalize(source_code)

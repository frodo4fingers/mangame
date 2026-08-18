"""Menu translations.

The whole UI is a handful of menu labels, so a plain dict per language beats
pulling in gettext and shipping .mo files. Missing keys fall back to English,
and an unknown language falls back to English wholesale, so a partial
translation can never blank out a menu entry.

There is one catalog per *reading* language (see
:mod:`mangame.i18n.languages`): the language you chose to read manga in is
also the language the menu speaks, which keeps the brief's tiny menu at one
language entry instead of two.
"""

from typing import Final

from mangame.i18n import languages
from mangame.i18n.languages import normalize

#: Language code -> the name shown to the user, in that language.
LANGUAGES: Final[dict[str, str]] = languages.labels()

_EN: Final[dict[str, str]] = {
    "menu.manga": "Manga",
    "menu.language": "Language",
    "menu.autostart": "Start on login",
    "menu.quit": "Quit mangame",
    "menu.add": "Add manga…",
    "menu.refresh": "Check now",
    "menu.remove": "Stop tracking",
    "menu.mark_read": "Mark as read",
    "menu.open": "Open chapter",
    "menu.no_series": "No manga tracked yet",
    "state.ready": "ready to read",
    "state.due": "waiting for the next chapter",
    "state.break": "on break",
    "notify.new_chapter": "New chapter available",
    "notify.break": "Break announced",
    "dialog.add.title": "Add manga",
    "dialog.add.prompt": "Search for a series to track.",
    "dialog.add.placeholder": "Series title",
    "dialog.add.search": "Search",
    "dialog.add.add": "Add",
    "dialog.add.searching": "Searching…",
    "dialog.add.results": "{count} found — pick one and choose Add.",
    "dialog.add.none": "Nothing found for “{query}”. Try another spelling.",
    "dialog.add.failed": "The search could not be completed. Try again.",
    "dialog.add.tracked": "already tracked",
    "tooltip.checking": "checking…",
}

_CATALOGS: Final[dict[str, dict[str, str]]] = {
    "en": _EN,
    "de": {
        "menu.manga": "Manga",
        "menu.language": "Sprache",
        "menu.autostart": "Beim Anmelden starten",
        "menu.quit": "mangame beenden",
        "menu.add": "Manga hinzufügen…",
        "menu.refresh": "Jetzt prüfen",
        "menu.remove": "Nicht mehr verfolgen",
        "menu.mark_read": "Als gelesen markieren",
        "menu.open": "Kapitel öffnen",
        "menu.no_series": "Noch kein Manga verfolgt",
        "state.ready": "bereit zum Lesen",
        "state.due": "wartet auf das nächste Kapitel",
        "state.break": "pausiert",
        "notify.new_chapter": "Neues Kapitel verfügbar",
        "notify.break": "Pause angekündigt",
        "dialog.add.title": "Manga hinzufügen",
        "dialog.add.prompt": "Serie suchen, die verfolgt werden soll.",
        "dialog.add.placeholder": "Titel der Serie",
        "dialog.add.search": "Suchen",
        "dialog.add.add": "Hinzufügen",
        "dialog.add.searching": "Wird gesucht…",
        "dialog.add.results": "{count} gefunden — eine auswählen und hinzufügen.",
        "dialog.add.none": "Nichts zu „{query}“ gefunden. Andere Schreibweise versuchen.",
        "dialog.add.failed": "Die Suche konnte nicht abgeschlossen werden. Bitte erneut versuchen.",
        "dialog.add.tracked": "wird bereits verfolgt",
        "tooltip.checking": "wird geprüft…",
    },
    "es": {
        "menu.manga": "Manga",
        "menu.language": "Idioma",
        "menu.autostart": "Iniciar al iniciar sesión",
        "menu.quit": "Salir de mangame",
        "menu.add": "Añadir manga…",
        "menu.refresh": "Comprobar ahora",
        "menu.remove": "Dejar de seguir",
        "menu.mark_read": "Marcar como leído",
        "menu.open": "Abrir capítulo",
        "menu.no_series": "Aún no sigues ningún manga",
        "state.ready": "listo para leer",
        "state.due": "esperando el próximo capítulo",
        "state.break": "en pausa",
        "notify.new_chapter": "Nuevo capítulo disponible",
        "notify.break": "Pausa anunciada",
        "dialog.add.title": "Añadir manga",
        "dialog.add.prompt": "Busca una serie para seguirla.",
        "dialog.add.placeholder": "Título de la serie",
        "dialog.add.search": "Buscar",
        "dialog.add.add": "Añadir",
        "dialog.add.searching": "Buscando…",
        "dialog.add.results": "{count} encontradas — elige una y pulsa Añadir.",
        "dialog.add.none": "Sin resultados para «{query}». Prueba con otra grafía.",
        "dialog.add.failed": "No se pudo completar la búsqueda. Inténtalo de nuevo.",
        "dialog.add.tracked": "ya la sigues",
        "tooltip.checking": "comprobando…",
    },
}


class Translator:
    """Looks up a menu label, falling back to English key by key."""

    def __init__(self, language: str = "en") -> None:
        self.language = normalize(language)
        self._catalog = _CATALOGS[self.language]

    def __call__(self, key: str) -> str:
        return self._catalog.get(key) or _EN.get(key, key)


def available() -> dict[str, str]:
    """Languages with a catalog, as ``{code: endonym}``, in menu order."""
    return {code: label for code, label in LANGUAGES.items() if code in _CATALOGS}

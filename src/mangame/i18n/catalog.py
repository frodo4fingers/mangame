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
    "dialog.settings.title": "mangame settings",
    "dialog.settings.tab.general": "General",
    "dialog.settings.tab.manga": "Manga",
    "dialog.settings.tab.artwork": "Artwork",
    "dialog.settings.language": "Reading language",
    "dialog.settings.language_hint": (
        "Only sources that publish in this language are polled, and the menu speaks it too."
    ),
    "dialog.settings.autostart_unsupported": "Not available on this desktop",
    "dialog.settings.notifications": "Notify me about new chapters",
    "dialog.settings.tray.heading": "Tray icons",
    "dialog.settings.tray.one": "One icon for everything",
    "dialog.settings.tray.each": "One icon per manga",
    "dialog.settings.tray.each_hint": "Each manga wears the emblem you chose for it under Manga.",
    "dialog.settings.column.series": "Series",
    "dialog.settings.column.emblem": "Emblem",
    "dialog.settings.tray_hint": (
        "Unticked series are still tracked; they just do not get their own tray icon."
    ),
    "dialog.settings.emblem.monogram": "Generated badge",
    "dialog.settings.art.image": "Picture",
    "dialog.settings.art.images": "Images",
    "dialog.settings.art.choose": "Choose…",
    "dialog.settings.art.for": "Use for",
    "dialog.settings.art.for.none": "Choose a manga…",
    "dialog.settings.art.for.shared": "A shared emblem…",
    "dialog.settings.art.name": "Emblem name",
    "dialog.settings.art.verdict.matched": "“{name}” matches {title}.",
    "dialog.settings.art.verdict.chosen": "{title} will wear this picture.",
    "dialog.settings.art.verdict.none": (
        "“{name}” matches none of your manga. Pick one above, or save it as a shared emblem."
    ),
    "dialog.settings.art.verdict.shared": "Saved under a name any manga can wear.",
    "dialog.settings.art.tone": "Break style",
    "dialog.settings.art.tone.dark": "Dark silhouette, light rim",
    "dialog.settings.art.tone.light": "Light silhouette, dark rim",
    "dialog.settings.art.preview": "Preview on a light and a dark panel",
    "dialog.settings.art.prompt": "Pick a PNG or SVG to turn into a tray emblem",
    "dialog.settings.art.import": "Add emblem",
    "dialog.settings.art.import.for": "Use for {title}",
    "dialog.settings.art.assigned": "{title} now wears this picture.",
    "dialog.settings.art.installed": "Added “{name}”. Pick it for a series under Manga.",
    "dialog.settings.art.removed": "Removed “{name}”.",
    "dialog.settings.art.failed": "That file could not be read as a picture.",
    "dialog.settings.art.yours": "Your artwork",
    "dialog.settings.art.none": "Nothing imported yet",
    "dialog.settings.art.unused": "not used by any manga",
    "dialog.settings.art.remove": "Remove",
    "menu.settings": "Settings…",
    "tooltip.checking": "checking…",
}

_CATALOGS: Final[dict[str, dict[str, str]]] = {
    "en": _EN,
    "de": {
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
        "dialog.settings.title": "mangame-Einstellungen",
        "dialog.settings.tab.general": "Allgemein",
        "dialog.settings.tab.manga": "Manga",
        "dialog.settings.tab.artwork": "Bildmarken",
        "dialog.settings.language": "Lesesprache",
        "dialog.settings.language_hint": (
            "Nur Quellen, die in dieser Sprache veröffentlichen, werden abgefragt — "
            "und das Menü spricht sie ebenfalls."
        ),
        "dialog.settings.autostart_unsupported": "Auf dieser Arbeitsumgebung nicht verfügbar",
        "dialog.settings.notifications": "Über neue Kapitel benachrichtigen",
        "dialog.settings.tray.heading": "Symbole im Infobereich",
        "dialog.settings.tray.one": "Ein Symbol für alles",
        "dialog.settings.tray.each": "Ein Symbol pro Manga",
        "dialog.settings.tray.each_hint": "Jeder Manga trägt sein Emblem aus dem Tab „Manga“.",
        "dialog.settings.column.series": "Serie",
        "dialog.settings.column.emblem": "Bildmarke",
        "dialog.settings.tray_hint": (
            "Nicht angehakte Serien werden weiter verfolgt, sie bekommen nur kein eigenes Symbol."
        ),
        "dialog.settings.emblem.monogram": "Erzeugtes Abzeichen",
        "dialog.settings.art.image": "Bild",
        "dialog.settings.art.images": "Bilder",
        "dialog.settings.art.choose": "Auswählen…",
        "dialog.settings.art.for": "Verwenden für",
        "dialog.settings.art.for.none": "Manga wählen…",
        "dialog.settings.art.for.shared": "Gemeinsame Bildmarke…",
        "dialog.settings.art.name": "Name der Bildmarke",
        "dialog.settings.art.verdict.matched": "„{name}“ passt zu {title}.",
        "dialog.settings.art.verdict.chosen": "{title} bekommt dieses Bild.",
        "dialog.settings.art.verdict.none": (
            "„{name}“ passt zu keinem deiner Manga. Oben einen auswählen "
            "oder als gemeinsame Bildmarke sichern."
        ),
        "dialog.settings.art.verdict.shared": (
            "Wird unter einem Namen gesichert, den jeder Manga tragen kann."
        ),
        "dialog.settings.art.tone": "Pausen-Darstellung",
        "dialog.settings.art.tone.dark": "Dunkle Silhouette, heller Rand",
        "dialog.settings.art.tone.light": "Helle Silhouette, dunkler Rand",
        "dialog.settings.art.preview": "Vorschau auf hellem und dunklem Panel",
        "dialog.settings.art.prompt": "PNG oder SVG wählen, das zur Bildmarke werden soll",
        "dialog.settings.art.import": "Bildmarke anlegen",
        "dialog.settings.art.import.for": "Für {title} verwenden",
        "dialog.settings.art.assigned": "{title} trägt jetzt dieses Bild.",
        "dialog.settings.art.installed": "„{name}“ angelegt. Unter Manga einer Serie zuweisen.",
        "dialog.settings.art.removed": "„{name}“ entfernt.",
        "dialog.settings.art.failed": "Diese Datei konnte nicht als Bild gelesen werden.",
        "dialog.settings.art.yours": "Eigene Bildmarken",
        "dialog.settings.art.none": "Noch nichts angelegt",
        "dialog.settings.art.unused": "von keinem Manga verwendet",
        "dialog.settings.art.remove": "Entfernen",
        "menu.settings": "Einstellungen…",
        "tooltip.checking": "wird geprüft…",
    },
    "es": {
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
        "dialog.settings.title": "Ajustes de mangame",
        "dialog.settings.tab.general": "General",
        "dialog.settings.tab.manga": "Manga",
        "dialog.settings.tab.artwork": "Emblemas",
        "dialog.settings.language": "Idioma de lectura",
        "dialog.settings.language_hint": (
            "Solo se consultan fuentes que publican en este idioma, y el menú también lo habla."
        ),
        "dialog.settings.autostart_unsupported": "No disponible en este escritorio",
        "dialog.settings.notifications": "Avisarme de capítulos nuevos",
        "dialog.settings.tray.heading": "Iconos en la bandeja",
        "dialog.settings.tray.one": "Un icono para todo",
        "dialog.settings.tray.each": "Un icono por manga",
        "dialog.settings.tray.each_hint": "Cada manga lleva el emblema que elegiste en Manga.",
        "dialog.settings.column.series": "Serie",
        "dialog.settings.column.emblem": "Emblema",
        "dialog.settings.tray_hint": (
            "Las series sin marcar se siguen igual; solo no reciben su propio icono en la bandeja."
        ),
        "dialog.settings.emblem.monogram": "Insignia generada",
        "dialog.settings.art.image": "Imagen",
        "dialog.settings.art.images": "Imágenes",
        "dialog.settings.art.choose": "Elegir…",
        "dialog.settings.art.for": "Usar para",
        "dialog.settings.art.for.none": "Elige un manga…",
        "dialog.settings.art.for.shared": "Un emblema compartido…",
        "dialog.settings.art.name": "Nombre del emblema",
        "dialog.settings.art.verdict.matched": "«{name}» coincide con {title}.",
        "dialog.settings.art.verdict.chosen": "{title} llevará esta imagen.",
        "dialog.settings.art.verdict.none": (
            "«{name}» no coincide con ninguno de tus mangas. Elige uno arriba "
            "o guárdalo como emblema compartido."
        ),
        "dialog.settings.art.verdict.shared": (
            "Se guarda con un nombre que cualquier manga puede llevar."
        ),
        "dialog.settings.art.tone": "Estilo en pausa",
        "dialog.settings.art.tone.dark": "Silueta oscura, borde claro",
        "dialog.settings.art.tone.light": "Silueta clara, borde oscuro",
        "dialog.settings.art.preview": "Vista previa sobre panel claro y oscuro",
        "dialog.settings.art.prompt": "Elige un PNG o SVG para convertirlo en emblema",
        "dialog.settings.art.import": "Crear emblema",
        "dialog.settings.art.import.for": "Usar para {title}",
        "dialog.settings.art.assigned": "{title} ya lleva esta imagen.",
        "dialog.settings.art.installed": "«{name}» creado. Asígnalo a una serie en Manga.",
        "dialog.settings.art.removed": "«{name}» eliminado.",
        "dialog.settings.art.failed": "No se pudo leer ese archivo como imagen.",
        "dialog.settings.art.yours": "Tus emblemas",
        "dialog.settings.art.none": "Todavía no has creado ninguno",
        "dialog.settings.art.unused": "ningún manga lo usa",
        "dialog.settings.art.remove": "Eliminar",
        "menu.settings": "Ajustes…",
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

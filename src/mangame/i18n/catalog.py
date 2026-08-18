"""Menu translations.

The whole UI is a handful of menu labels, so a plain dict per language beats
pulling in gettext and shipping .mo files. Missing keys fall back to English,
and an unknown language falls back to English wholesale, so a partial
translation can never blank out a menu entry.
"""

from typing import Final

#: Language code -> the name shown to the user, in that language.
LANGUAGES: Final[dict[str, str]] = {
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "pt-br": "Português (BR)",
    "it": "Italiano",
    "ja": "日本語",
}

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
    "dialog.add.prompt": "Search for a series:",
    "dialog.add.none": "Nothing found.",
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
        "dialog.add.prompt": "Serie suchen:",
        "dialog.add.none": "Nichts gefunden.",
        "tooltip.checking": "wird geprüft…",
    },
    "fr": {
        "menu.manga": "Mangas",
        "menu.language": "Langue",
        "menu.autostart": "Lancer à la connexion",
        "menu.quit": "Quitter mangame",
        "menu.add": "Ajouter un manga…",
        "menu.refresh": "Vérifier maintenant",
        "menu.remove": "Ne plus suivre",
        "menu.mark_read": "Marquer comme lu",
        "menu.open": "Ouvrir le chapitre",
        "menu.no_series": "Aucun manga suivi",
        "state.ready": "prêt à lire",
        "state.due": "en attente du prochain chapitre",
        "state.break": "en pause",
        "notify.new_chapter": "Nouveau chapitre disponible",
        "notify.break": "Pause annoncée",
        "dialog.add.title": "Ajouter un manga",
        "dialog.add.prompt": "Rechercher une série :",
        "dialog.add.none": "Aucun résultat.",
        "tooltip.checking": "vérification…",
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
        "dialog.add.prompt": "Buscar una serie:",
        "dialog.add.none": "Sin resultados.",
        "tooltip.checking": "comprobando…",
    },
    "pt-br": {
        "menu.manga": "Mangá",
        "menu.language": "Idioma",
        "menu.autostart": "Iniciar ao entrar",
        "menu.quit": "Sair do mangame",
        "menu.add": "Adicionar mangá…",
        "menu.refresh": "Verificar agora",
        "menu.remove": "Parar de acompanhar",
        "menu.mark_read": "Marcar como lido",
        "menu.open": "Abrir capítulo",
        "menu.no_series": "Nenhum mangá acompanhado",
        "state.ready": "pronto para ler",
        "state.due": "aguardando o próximo capítulo",
        "state.break": "em pausa",
        "notify.new_chapter": "Novo capítulo disponível",
        "notify.break": "Pausa anunciada",
        "dialog.add.title": "Adicionar mangá",
        "dialog.add.prompt": "Procurar uma série:",
        "dialog.add.none": "Nada encontrado.",
        "tooltip.checking": "verificando…",
    },
    "it": {
        "menu.manga": "Manga",
        "menu.language": "Lingua",
        "menu.autostart": "Avvia all'accesso",
        "menu.quit": "Esci da mangame",
        "menu.add": "Aggiungi manga…",
        "menu.refresh": "Controlla ora",
        "menu.remove": "Non seguire più",
        "menu.mark_read": "Segna come letto",
        "menu.open": "Apri capitolo",
        "menu.no_series": "Nessun manga seguito",
        "state.ready": "pronto da leggere",
        "state.due": "in attesa del prossimo capitolo",
        "state.break": "in pausa",
        "notify.new_chapter": "Nuovo capitolo disponibile",
        "notify.break": "Pausa annunciata",
        "dialog.add.title": "Aggiungi manga",
        "dialog.add.prompt": "Cerca una serie:",
        "dialog.add.none": "Nessun risultato.",
        "tooltip.checking": "controllo…",
    },
    "ja": {
        "menu.manga": "マンガ",
        "menu.language": "言語",
        "menu.autostart": "ログイン時に起動",
        "menu.quit": "mangame を終了",
        "menu.add": "マンガを追加…",
        "menu.refresh": "今すぐ確認",
        "menu.remove": "追跡をやめる",
        "menu.mark_read": "既読にする",
        "menu.open": "話を開く",
        "menu.no_series": "追跡中のマンガはありません",
        "state.ready": "読めます",
        "state.due": "次話を待っています",
        "state.break": "休載中",
        "notify.new_chapter": "新しい話が公開されました",
        "notify.break": "休載が告知されました",
        "dialog.add.title": "マンガを追加",
        "dialog.add.prompt": "シリーズを検索:",
        "dialog.add.none": "見つかりませんでした。",
        "tooltip.checking": "確認中…",
    },
}


def normalize(language: str) -> str:
    """Best available catalog for a language tag.

    Accepts whatever a config file or an OS locale offers — ``pt-BR``,
    ``de_DE.UTF-8``, ``EN`` — and degrades to the base language before giving
    up on English.
    """
    tag = language.strip().replace("_", "-").split(".")[0].lower()
    if tag in _CATALOGS:
        return tag
    base = tag.split("-")[0]
    if base in _CATALOGS:
        return base
    return "en"


class Translator:
    """Looks up a menu label, falling back to English key by key."""

    def __init__(self, language: str = "en") -> None:
        self.language = normalize(language)
        self._catalog = _CATALOGS[self.language]

    def __call__(self, key: str) -> str:
        return self._catalog.get(key) or _EN.get(key, key)


def available() -> dict[str, str]:
    """Languages with a catalog, as ``{code: endonym}``."""
    return {code: LANGUAGES[code] for code in _CATALOGS if code in LANGUAGES}

"""Names shared by dropped artwork, generated files and tray lookup."""


def emblem_name(raw: str) -> str:
    """Fold a title or user name into something usable as a directory name."""
    cleaned = "".join(char if char.isalnum() else "-" for char in raw.strip().lower())
    return "-".join(part for part in cleaned.split("-") if part)

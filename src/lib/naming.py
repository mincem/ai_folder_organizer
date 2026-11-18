"""Folder names: building them, making them valid on Windows, and comparing titles loosely."""
import re
import unicodedata

# Windows doesn't allow these characters in names (':' is replaced instead, see sanitize)
REMOVED_CHARS = '<>"/\\|?*'


def build_new_name(series: str, volume: int | None, title: str | None) -> str:
    name = sanitize(series)
    if volume is not None:
        name += f" v{volume:02d}"
    if title:
        name += f" [{sanitize(title)}]"
    return name


def sanitize(text: str) -> str:
    # Windows doesn't allow these characters, nor names ending in a dot or space
    text = text.replace(':', ' - ')
    text = re.sub(f'[{re.escape(REMOVED_CHARS)}]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip(' .')


def describe_sanitize(text: str) -> list[str]:
    """What sanitize changes in the text, to show the user."""
    changes = []
    if ':' in text:
        changes.append("replaced ':' with '-'")
    removed = sorted({c for c in text if c in REMOVED_CHARS})
    if removed:
        changes.append(f"removed {', '.join(repr(c) for c in removed)}")
    if text.rstrip().endswith('.'):
        changes.append("removed trailing '.'")
    return changes


def normalize(text: str) -> str:
    """Ignores case, accents and punctuation, to match titles the AI may spell slightly differently."""
    without_accents = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    return re.sub(r'\W', '', without_accents.casefold())

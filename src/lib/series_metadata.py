import re

GENRES = [
    # AniList
    "Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy", "Horror", "Mahou Shoujo", "Mecha", "Music",
    "Mystery", "Psychological", "Romance", "Sci-Fi", "Slice of Life", "Sports", "Supernatural", "Thriller",
    # Western comics (Grand Comics Database)
    "Superhero", "Crime", "War", "Western", "Historical",
]

# MyAnimeList demographics, stored in the genre field like any other genre
DEMOGRAPHICS = ["Shounen", "Seinen", "Shoujo", "Josei", "Kids"]

NULLABLE_STRING = {"type": ["string", "null"]}

# Series-level fields asked from the AI. To add one, add it here; the response schema,
# the validation, the confirmation display and the cache all follow this list.
SERIES_FIELDS = {
    "writer": {**NULLABLE_STRING, "description": "Writer of the series."},
    "penciller": {**NULLABLE_STRING, "description": "Penciller of the series. For manga, usually the writer."},
    "publisher": {**NULLABLE_STRING, "description": "Publisher of the edition, as described in the instructions."},
    "imprint": {**NULLABLE_STRING,
                "description": "Imprint within the publisher (e.g. Vertigo, Black Label). Usually null for manga."},
    "genre": {
        "type": "array",
        "items": {"type": "string", "enum": GENRES + DEMOGRAPHICS},
        "description": "Genres of the series, plus its demographic when one applies. Empty if unknown.",
    },
}


def clean_series_item(item: dict) -> dict:
    """Keeps the known fields, as a string or None. Lists, like genre, are joined with commas."""
    cleaned = {}
    for name, field in SERIES_FIELDS.items():
        value = item.get(name)
        if isinstance(value, list):
            allowed = field.get('items', {}).get('enum')
            values = [v.strip() for v in value if isinstance(v, str) and v.strip()]
            unknown = [v for v in values if allowed and v not in allowed]
            if unknown:
                print(f"Warning: ignoring unknown {name} for '{item['series']}': {', '.join(unknown)}")
            value = ', '.join(dict.fromkeys(v for v in values if v not in unknown))
        cleaned[name] = (value.strip() or None) if isinstance(value, str) else None
    notes = item.get('notes')
    cleaned["notes"] = (notes.strip() or None) if isinstance(notes, str) else None
    return cleaned


def clean_language(language) -> str | None:
    """Returns a lowercase ISO 639-1 code, or None if there's none or it isn't valid."""
    if language is None:
        return None
    code = language.strip().lower() if isinstance(language, str) else None
    if not code or not re.fullmatch(r'[a-z]{2}', code):
        print(f"Warning: AI returned an invalid language code {language!r}, ignoring it.")
        return None
    return code

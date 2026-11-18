"""Asking the AI about the folders: the prompt and schema, the request, and checking the response."""
import json
import os
import time

from .ai_client import AIError
from .ai_service import AIService
from .entry import Entry
from .logger import Logger
from .naming import normalize, sanitize
from .series_metadata import DEMOGRAPHICS, GENRES, SERIES_FIELDS, clean_language, clean_series_item

NOTES_FIELD = {
    "type": ["string", "null"],
    "description": "Short remark for the user about what to double-check, only for tough calls. Null otherwise.",
}

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "description": "One entry per folder name, in the same order as the input.",
            "items": {
                "type": "object",
                "properties": {
                    "original": {"type": "string", "description": "The folder name exactly as given, unchanged."},
                    "series": {"type": "string", "description": "The series title."},
                    "volume": {"type": ["integer", "null"], "description": "The volume number, or null if none."},
                    "title": {"type": ["string", "null"], "description": "The folder title, or null if none."},
                    "notes": NOTES_FIELD,
                },
                "required": ["original", "series", "volume", "title", "notes"],
            },
        },
        "series": {
            "type": "array",
            "description": "One item per series in the entries.",
            "items": {
                "type": "object",
                "properties": {
                    "series": {"type": "string", "description": "The series title, exactly as in the entries."},
                    **SERIES_FIELDS,
                    "notes": NOTES_FIELD,
                },
                "required": ["series", *SERIES_FIELDS, "notes"],
            },
        },
        "language_iso": {
            "type": ["string", "null"],
            "description": "ISO 639-1 code of the editions' language (e.g. \"es\"), as described in the instructions.",
        },
    },
    "required": ["entries", "series", "language_iso"],
}


class AIRequest:
    def __init__(self, ai_service: AIService, logger: Logger):
        self.ai_service = ai_service
        self.logger = logger

    def get_entries(self, folders: list[str], root_folder: str,
                    country: str | None) -> tuple[list[Entry], dict[str, dict]]:
        """Returns the valid entries and the series metadata keyed by series title.

        Raises AIError if the request fails, and json.JSONDecodeError or ValueError if the response is unusable."""
        prompt = get_prompt(folders, country)
        response = self.ask_ai(prompt, len(folders), root_folder, country)

        parsed = parse_response(response)
        entries = validate_entries(parsed.get('entries'), folders)
        metadata = validate_series(parsed.get('series'), entries)
        # The language is the same for the whole run, so it comes once and is copied to each series
        language_iso = clean_language(parsed.get('language_iso'))
        metadata = {series: {'language_iso': language_iso, **item} for series, item in metadata.items()}
        print(f"  {len(entries)} entries, {len(metadata)} series, language: {language_iso or '-'}")
        return entries, metadata

    def ask_ai(self, prompt: str, folder_count: int, root_folder: str, country: str | None) -> str:
        model = self.ai_service.model_name.removeprefix('models/')
        if self.ai_service.is_cached(prompt):
            print(f"Using cached response for {folder_count} folders (no request sent)")
        else:
            # flush, so the line shows up while waiting for the response
            print(f"Asking {model} about {folder_count} folders...", end='', flush=True)

        start = time.monotonic()
        try:
            response = self.ai_service.ask(prompt, RESPONSE_SCHEMA)
        except AIError:
            if not self.ai_service.is_cached(prompt):
                print(" failed")
            raise
        seconds = time.monotonic() - start

        if not response.cached:
            tokens = f", {response.tokens / 1000:.1f}k tokens" if response.tokens else ''
            print(f" done in {seconds:.1f}s{tokens}")
        if response.problem:
            print(f"  Warning: {response.problem}")
        # Saved before parsing, so the log is there when the response turns out to be wrong
        log_path = self.logger.save_ai_log(prompt, response, model, seconds, root_folder, country)
        if log_path:
            print(f"  Prompt and response saved to {log_path}")
        return response.text


def get_prompt(folders: list[str], country: str = None) -> str:
    prompt_file_path = os.path.join(os.path.dirname(__file__), 'prompt.md')
    with open(prompt_file_path, 'r', encoding='utf-8') as f:
        prompt = f.read()

    if country:
        country_rule = (f"Publisher and imprint depend on the edition, which is published in {country}. "
                        "Give the ones of that country's edition, not the original ones. If you can't find "
                        "that edition, use null for just these two and say so in notes. For `language_iso`, "
                        "give the ISO 639-1 code of that country's main language (e.g. Argentina -> \"es\").")
    else:
        country_rule = "Publisher and imprint are the original ones. `language_iso` is null."

    # Plain replacements, so other braces in the prompt don't need escaping
    replacements = {
        '{country}': country_rule,
        '{genres}': ', '.join(GENRES),
        '{demographics}': ', '.join(DEMOGRAPHICS),
        '{folders}': '\n'.join(folders),
    }
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt


def parse_response(response: str) -> dict:
    parsed = json.loads(response)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object with entries and series")
    return parsed


def validate_entries(entries, folders: list[str]) -> list[Entry]:
    """Turns the AI's entries into Entry objects, skipping the unusable ones with a warning."""
    if not isinstance(entries, list):
        raise ValueError("Expected a JSON array of entries")

    pending = set(folders)
    valid = []
    for entry in entries:
        original = entry.get('original') if isinstance(entry, dict) else None
        if original not in pending:
            print(f"Warning: AI returned an unknown or repeated folder '{original}', ignoring it.")
            continue
        pending.remove(original)
        series, volume = entry.get('series'), entry.get('volume')
        if not isinstance(series, str) or not sanitize(series):
            print(f"Warning: AI returned no series title for '{original}', skipping.")
            continue
        # bool is a subclass of int, but True isn't a volume
        if volume is not None and (not isinstance(volume, int) or isinstance(volume, bool)):
            print(f"Warning: AI returned an invalid volume {volume!r} for '{original}', skipping.")
            continue
        valid.append(Entry(original, series, volume, optional_text(entry.get('title')),
                           optional_text(entry.get('notes'))))

    for folder in folders:
        if folder in pending:
            print(f"Warning: AI returned nothing for '{folder}', skipping.")
    return valid


def validate_series(items, entries: list[Entry]) -> dict[str, dict]:
    """Returns the metadata keyed by the series title used in the entries."""
    if not isinstance(items, list):
        print("Warning: AI returned no series metadata.")
        return {}

    # Match loosely, in case the AI spelled the title slightly differently than in the entries
    titles = {normalize(entry.series): entry.series for entry in entries}
    metadata = {}
    for item in items:
        name = item.get('series') if isinstance(item, dict) else None
        series = titles.get(normalize(name)) if isinstance(name, str) else None
        if series is None or series in metadata:
            print(f"Warning: AI returned metadata for an unknown or repeated series '{name}', ignoring it.")
            continue
        metadata[series] = clean_series_item({**item, 'series': series})

    for series in dict.fromkeys(entry.series for entry in entries):
        if series not in metadata:
            print(f"Warning: AI returned no metadata for '{series}'.")
    return metadata


def optional_text(value) -> str | None:
    """The stripped text, or None if it's empty or not a string."""
    return (value.strip() or None) if isinstance(value, str) else None

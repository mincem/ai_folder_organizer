import json
import os
import re
import time
import unicodedata
from collections import Counter

from .ai_client import AIError
from .ai_service import AIService
from .logger import Logger
from .metadata_cache import MetadataCache
from .series_metadata import DEMOGRAPHICS, GENRES, SERIES_FIELDS, clean_language, clean_series_item

REMOVED_CHARS = '<>"/\\|?*'

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


class Command:
    def __init__(
        self,
        root_folder: str,
        country: str | None,
        ai_service: AIService,
        metadata_cache: MetadataCache,
        logger: Logger,
    ):
        if not os.path.isdir(root_folder):
            raise ValueError(f"The provided path is not a valid directory: {root_folder}")
        self.root_folder = root_folder
        self.country = country

        self.ai_service = ai_service
        self.metadata_cache = metadata_cache
        self.logger = logger

    def execute(self):
        self.rename_folders()

    def rename_folders(self):
        try:
            items = os.listdir(self.root_folder)
        except OSError as e:
            print(f"Error accessing {self.root_folder}: {e}")
            return

        folders = [item for item in items if os.path.isdir(os.path.join(self.root_folder, item))]
        self.logger.log_folders(folders, self.root_folder)

        if not folders:
            return

        try:
            entries, metadata = self.get_entries(folders)
        except AIError as e:
            print(f"Error getting a response from the AI: {e}")
            return
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing AI response: {e}")
            return

        approved = self.confirm_renames(entries, self.drop_conflicts(entries), metadata)

        print()
        for entry in approved:
            self.rename_folder(entry['original'], entry['new_name'])
        self.logger.print_completion_status(self.metadata_cache.path)

    def rename_folder(self, current_name: str, new_name: str):
        original_path = os.path.join(self.root_folder, current_name)
        if not os.path.exists(original_path):
            print(f"Warning: Original folder '{current_name}' not found, skipping.")
            return

        new_path = os.path.join(self.root_folder, new_name)
        try:
            os.rename(original_path, new_path)
        except OSError as e:
            print(f"Error renaming '{current_name}': {e}")
            return
        print(f"Renamed: '{current_name}' -> '{new_name}'")
        self.logger.increment_successful_renames()

    def confirm_renames(self, entries: list[dict], renamable: list[dict], metadata: dict[str, dict]) -> list[dict]:
        to_rename = {entry['original'] for entry in renamable if entry['new_name'] != entry['original']}
        unchanged = len(renamable) - len(to_rename)
        if unchanged:
            print(f"\n{unchanged} folders already have the right name.")

        # Group all entries, not only the renamable ones, so warnings consider the whole series
        groups = self.group_by_series(entries)
        cached = [series for series in groups if self.is_cached(series)]
        if cached:
            print(f"{len(cached)} series already have saved metadata, keeping it.")

        approved = []
        for series, group in groups.items():
            pending = [entry for entry in group if entry['original'] in to_rename]
            new_metadata = None if series in cached else metadata.get(series)
            if not pending:
                if new_metadata and self.confirm_metadata(series, new_metadata):
                    self.save_metadata(series, new_metadata)
                continue
            warnings = self.series_warnings(series, group, list(groups))
            if len(pending) == 1:
                confirmed = self.confirm_each(pending, warnings, new_metadata)
            else:
                confirmed = self.confirm_series(series, pending, warnings, new_metadata)
            # A single yes/no covers both the renames and the metadata
            if confirmed and new_metadata:
                self.save_metadata(series, new_metadata)
            approved += confirmed
        return approved

    def confirm_series(self, series: str, entries: list[dict], warnings: list[str],
                       metadata: dict = None) -> list[dict]:
        print(f"\n{series}: {len(entries)} folders")
        for entry in entries:
            self.print_entry(entry)
        self.print_metadata(series, metadata)
        self.print_warnings(warnings)

        while True:
            response = input("Rename all? [Y]es / [r]eview each / [n]o: ").strip().lower()
            if response in ('', 'y', 'yes'):
                return entries
            if response in ('r', 'review'):
                return self.confirm_each(entries, [])
            if response in ('n', 'no'):
                print(f"Not renamed: {series}")
                return []

    def confirm_each(self, entries: list[dict], warnings: list[str], metadata: dict = None) -> list[dict]:
        approved = []
        for entry in entries:
            print()
            self.print_entry(entry)
            self.print_metadata(entry['series'], metadata)
            self.print_warnings(warnings)
            response = input("Rename? [Y/n]: ").strip().lower()
            if response in ('', 'y', 'yes'):
                approved.append(entry)
            else:
                print(f"Not renamed: '{entry['original']}'")
        return approved

    def confirm_metadata(self, series: str, metadata: dict) -> bool:
        print(f"\n{series}: folders already have the right name")
        self.print_metadata(series, metadata)
        response = input("Save metadata? [Y/n]: ").strip().lower()
        if response in ('', 'y', 'yes'):
            return True
        print(f"Metadata not saved: {series}")
        return False

    def is_cached(self, series: str) -> bool:
        cached = self.metadata_cache.get(series)
        return cached is not None and self.same_country(cached.get('country'), self.country)

    @staticmethod
    def same_country(first: str | None, second: str | None) -> bool:
        return (first or '').strip().casefold() == (second or '').strip().casefold()

    def save_metadata(self, series: str, metadata: dict):
        self.metadata_cache.set(series, {'country': self.country, **metadata})
        self.logger.increment_saved_metadata()

    @staticmethod
    def print_entry(entry: dict):
        print(f"  '{entry['original']}' -> '{entry['new_name']}'")
        if entry['changes']:
            print(f"      changed: {'; '.join(entry['changes'])}")
        if entry.get('notes'):
            print(f"      note: {entry['notes']}")

    def print_metadata(self, series: str, metadata: dict | None):
        if not metadata:
            return
        edition = ', '.join(filter(None, [self.country, metadata.get('language_iso')]))
        print(f"  metadata{f' ({edition})' if edition else ''}:")
        for name in SERIES_FIELDS:
            print(f"      {name}: {metadata.get(name) or '-'}")
        if metadata.get('notes'):
            print(f"      note: {metadata['notes']}")
        cached = self.metadata_cache.get(series)
        if cached is not None:
            print(f"      replaces the saved metadata for country: {cached.get('country') or 'none'}")

    @staticmethod
    def print_warnings(warnings: list[str]):
        for warning in warnings:
            print(f"  Warning: {warning}")

    @staticmethod
    def group_by_series(entries: list[dict]) -> dict[str, list[dict]]:
        groups = {}
        for entry in entries:
            groups.setdefault(entry['series'], []).append(entry)
        for group in groups.values():
            group.sort(key=lambda e: (e['volume'] is None, e['volume'] or 0, e['original']))
        return groups

    @staticmethod
    def series_warnings(series: str, group: list[dict], all_series: list[str]) -> list[str]:
        warnings = []
        volumes = [entry['volume'] for entry in group if entry['volume'] is not None]

        repeated = sorted(volume for volume, count in Counter(volumes).items() if count > 1)
        if repeated:
            warnings.append(f"repeated volumes: {', '.join(f'v{v:02d}' for v in repeated)}")

        if volumes:
            missing = sorted(set(range(min(volumes), max(volumes) + 1)) - set(volumes))
            if len(missing) > 10:
                warnings.append(f"{len(missing)} missing volumes between v{min(volumes):02d} and v{max(volumes):02d}")
            elif missing:
                warnings.append(f"missing volumes: {', '.join(f'v{v:02d}' for v in missing)}")

        # The AI may split one series in two by spelling it differently
        similar = [other for other in all_series
                   if other != series and Command.normalize(other) == Command.normalize(series)]
        if similar:
            warnings.append(f"similar series title: {', '.join(repr(other) for other in similar)}")
        return warnings

    @staticmethod
    def normalize(text: str) -> str:
        without_accents = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
        return re.sub(r'\W', '', without_accents.casefold())

    def get_entries(self, folders: list[str]) -> tuple[list[dict], dict[str, dict]]:
        prompt = self.get_prompt(folders, self.country)
        response = self.ask_ai(prompt, len(folders))

        parsed = self.parse_response(response)
        entries = self.validate_entries(parsed.get('entries'), folders)
        metadata = self.validate_series(parsed.get('series'), entries)
        # The language is the same for the whole run, so it comes once and is copied to each series
        language_iso = clean_language(parsed.get('language_iso'))
        metadata = {series: {'language_iso': language_iso, **item} for series, item in metadata.items()}
        for entry in entries:
            entry['new_name'] = self.build_new_name(entry)
            changes = self.describe_sanitize(entry['series']) + self.describe_sanitize(entry.get('title') or '')
            entry['changes'] = list(dict.fromkeys(changes))
        print(f"  {len(entries)} entries, {len(metadata)} series, language: {language_iso or '-'}")
        return entries, metadata

    def ask_ai(self, prompt: str, folder_count: int) -> str:
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
        log_path = self.logger.save_ai_log(prompt, response, model, seconds, self.root_folder, self.country)
        if log_path:
            print(f"  Prompt and response saved to {log_path}")
        return response.text

    @staticmethod
    def validate_entries(entries, folders: list[str]) -> list[dict]:
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
            if not entry.get('series') or not Command.sanitize(entry['series']):
                print(f"Warning: AI returned no series title for '{original}', skipping.")
                continue
            valid.append(entry)

        for folder in folders:
            if folder in pending:
                print(f"Warning: AI returned nothing for '{folder}', skipping.")
        return valid

    @staticmethod
    def validate_series(items, entries: list[dict]) -> dict[str, dict]:
        """Returns the metadata keyed by the series title used in the entries."""
        if not isinstance(items, list):
            print("Warning: AI returned no series metadata.")
            return {}

        # Match loosely, in case the AI spelled the title slightly differently than in the entries
        titles = {Command.normalize(entry['series']): entry['series'] for entry in entries}
        metadata = {}
        for item in items:
            name = item.get('series') if isinstance(item, dict) else None
            series = titles.get(Command.normalize(name)) if isinstance(name, str) else None
            if series is None or series in metadata:
                print(f"Warning: AI returned metadata for an unknown or repeated series '{name}', ignoring it.")
                continue
            metadata[series] = clean_series_item({**item, 'series': series})

        for series in dict.fromkeys(entry['series'] for entry in entries):
            if series not in metadata:
                print(f"Warning: AI returned no metadata for '{series}'.")
        return metadata

    def drop_conflicts(self, entries: list[dict]) -> list[dict]:
        # Windows names are case-insensitive, so compare them casefolded
        targets = Counter(entry['new_name'].casefold() for entry in entries
                          if entry['new_name'] != entry['original'])

        valid = []
        for entry in entries:
            original, new_name = entry['original'], entry['new_name']
            is_case_only_change = original.casefold() == new_name.casefold()
            if original == new_name:
                valid.append(entry)
            elif targets[new_name.casefold()] > 1:
                print(f"Warning: more than one folder would be renamed to '{new_name}', skipping '{original}'.")
            elif not is_case_only_change and os.path.exists(os.path.join(self.root_folder, new_name)):
                print(f"Warning: '{new_name}' already exists, skipping '{original}'.")
            else:
                valid.append(entry)
        return valid

    @staticmethod
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

    @staticmethod
    def parse_response(response: str) -> dict:
        parsed = json.loads(response)
        if not isinstance(parsed, dict):
            raise ValueError("Expected a JSON object with entries and series")
        return parsed

    @staticmethod
    def build_new_name(entry: dict) -> str:
        name = Command.sanitize(entry['series'])
        if entry.get('volume') is not None:
            name += f" v{int(entry['volume']):02d}"
        if entry.get('title'):
            name += f" [{Command.sanitize(entry['title'])}]"
        return name

    @staticmethod
    def sanitize(text: str) -> str:
        # Windows doesn't allow these characters, nor names ending in a dot or space
        text = text.replace(':', ' - ')
        text = re.sub(f'[{re.escape(REMOVED_CHARS)}]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip(' .')

    @staticmethod
    def describe_sanitize(text: str) -> list[str]:
        changes = []
        if ':' in text:
            changes.append("replaced ':' with '-'")
        removed = sorted({c for c in text if c in REMOVED_CHARS})
        if removed:
            changes.append(f"removed {', '.join(repr(c) for c in removed)}")
        if text.rstrip().endswith('.'):
            changes.append("removed trailing '.'")
        return changes

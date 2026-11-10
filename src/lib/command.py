import json
import os
import re
import unicodedata
from collections import Counter

from .ai_client import AIError
from .ai_service import AIService
from .logger import Logger

REMOVED_CHARS = '<>"/\\|?*'

RESPONSE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "original": {"type": "string"},
            "series": {"type": "string"},
            "volume": {"type": ["integer", "null"]},
            "title": {"type": ["string", "null"]},
            "notes": {"type": ["string", "null"]},
        },
        "required": ["original", "series", "volume", "title", "notes"],
    },
}


class Command:
    def __init__(self, root_folder: str):
        if not os.path.isdir(root_folder):
            raise ValueError(f"The provided path is not a valid directory: {root_folder}")
        self.root_folder = root_folder
        print(f"Command initialized for folder: {self.root_folder}")

        self.ai_service = AIService()
        self.logger = Logger()

    def execute(self):
        print(f"\nExecuting command on: {self.root_folder}")
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
            entries = self.get_entries(folders)
        except AIError as e:
            print(f"Error getting a response from the AI: {e}")
            return
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing AI response: {e}")
            return

        approved = self.confirm_renames(entries, self.drop_conflicts(entries))

        print()
        for entry in approved:
            self.rename_folder(entry['original'], entry['new_name'])
        self.logger.print_completion_status()

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

    def confirm_renames(self, entries: list[dict], renamable: list[dict]) -> list[dict]:
        to_rename = {entry['original'] for entry in renamable if entry['new_name'] != entry['original']}
        unchanged = len(renamable) - len(to_rename)
        if unchanged:
            print(f"\n{unchanged} folders already have the right name.")

        # Group all entries, not only the renamable ones, so warnings consider the whole series
        groups = self.group_by_series(entries)
        approved = []
        for series, group in groups.items():
            pending = [entry for entry in group if entry['original'] in to_rename]
            if not pending:
                continue
            warnings = self.series_warnings(series, group, list(groups))
            if len(pending) == 1:
                approved += self.confirm_each(pending, warnings)
            else:
                approved += self.confirm_series(series, pending, warnings)
        return approved

    def confirm_series(self, series: str, entries: list[dict], warnings: list[str]) -> list[dict]:
        print(f"\n{series}: {len(entries)} folders")
        for entry in entries:
            self.print_entry(entry)
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

    def confirm_each(self, entries: list[dict], warnings: list[str]) -> list[dict]:
        approved = []
        for entry in entries:
            print()
            self.print_entry(entry)
            self.print_warnings(warnings)
            response = input("Rename? [Y/n]: ").strip().lower()
            if response in ('', 'y', 'yes'):
                approved.append(entry)
            else:
                print(f"Not renamed: '{entry['original']}'")
        return approved

    @staticmethod
    def print_entry(entry: dict):
        print(f"  '{entry['original']}' -> '{entry['new_name']}'")
        if entry['changes']:
            print(f"      changed: {'; '.join(entry['changes'])}")
        if entry.get('notes'):
            print(f"      note: {entry['notes']}")

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

    def get_entries(self, folders: list[str]) -> list[dict]:
        prompt = self.get_prompt("\n".join(folders))

        response = self.ai_service.ask(prompt, RESPONSE_SCHEMA)

        print("\n--- AI Response ---")
        print(response)
        print("-------------------------\n")

        entries = self.validate_entries(self.parse_entries_response(response), folders)
        for entry in entries:
            entry['new_name'] = self.build_new_name(entry)
            changes = self.describe_sanitize(entry['series']) + self.describe_sanitize(entry.get('title') or '')
            entry['changes'] = list(dict.fromkeys(changes))
        return entries

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
    def get_prompt(folder_list_str):
        prompt_file_path = os.path.join(os.path.dirname(__file__), 'prompt.md')
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        return prompt + "\n\n" + folder_list_str

    @staticmethod
    def parse_entries_response(response: str) -> list[dict]:
        return json.loads(response)

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

import json
import os
import re
from collections import Counter

from .ai_client import AIError
from .ai_service import AIService
from .logger import Logger

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

        for entry in self.drop_conflicts(entries):
            self.rename_folder(entry['original'], entry['new_name'])
        self.logger.print_completion_status()

    def rename_folder(self, current_name: str, new_name: str):
        if current_name == new_name:
            print(f"No change needed for: {current_name}")
            return

        original_path = os.path.join(self.root_folder, current_name)
        if not os.path.exists(original_path):
            print(f"Warning: Original folder '{current_name}' not found, skipping.")
            return

        new_path = os.path.join(self.root_folder, new_name)
        prompt_message = f"Rename '{current_name}' to '{new_name}'? [Y/n]: "
        response = input(prompt_message).strip().lower()

        if not response or response == 'y' or response == 'yes':
            try:
                os.rename(original_path, new_path)
            except OSError as e:
                print(f"Error renaming '{current_name}': {e}")
                return
            print(f"Renamed: '{current_name}' -> '{new_name}'")
            self.logger.increment_successful_renames()
        else:
            print(f"Not renamed: '{current_name}'")

    def get_entries(self, folders: list[str]) -> list[dict]:
        prompt = self.get_prompt("\n".join(folders))

        response = self.ai_service.ask(prompt, RESPONSE_SCHEMA)

        print("\n--- AI Response ---")
        print(response)
        print("-------------------------\n")

        entries = self.validate_entries(self.parse_entries_response(response), folders)
        for entry in entries:
            entry['new_name'] = self.build_new_name(entry)
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
        text = re.sub(r'[<>"/\\|?*]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip(' .')

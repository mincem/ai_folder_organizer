import json
import os

from .ai_client import AIError
from .ai_request import AIRequest
from .confirmation import Confirmer
from .logger import Logger
from .metadata_cache import MetadataCache
from .planning import add_new_names, drop_conflicts


class Command:
    def __init__(
        self,
        root_folder: str,
        country: str | None,
        ai_request: AIRequest,
        confirmer: Confirmer,
        metadata_cache: MetadataCache,
        logger: Logger,
    ):
        if not os.path.isdir(root_folder):
            raise ValueError(f"The provided path is not a valid directory: {root_folder}")
        self.root_folder = root_folder
        self.country = country

        self.ai_request = ai_request
        self.confirmer = confirmer
        self.metadata_cache = metadata_cache
        self.logger = logger

    def execute(self):
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
            entries, metadata = self.ai_request.get_entries(folders, self.root_folder, self.country)
        except AIError as e:
            print(f"Error getting a response from the AI: {e}")
            return
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing AI response: {e}")
            return

        add_new_names(entries)
        renamable = drop_conflicts(entries, self.root_folder)
        approved, metadata_to_save = self.confirmer.confirm(entries, renamable, metadata)

        for series, item in metadata_to_save.items():
            self.save_metadata(series, item)
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

    def save_metadata(self, series: str, metadata: dict):
        self.metadata_cache.set(series, {'country': self.country, **metadata})
        self.logger.increment_saved_metadata()

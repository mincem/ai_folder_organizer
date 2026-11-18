import json
import os

from .ai_client import AIError
from .ai_request import AIRequest
from .ai_service import AIService
from .confirmation import Confirmer
from .entry import Entry
from .logger import Logger
from .metadata_cache import MetadataCache
from .planning import drop_conflicts


def ask_retry(ai_service: AIService) -> bool:
    """Asks whether to try again, optionally with another model. True means retry."""
    while True:
        response = input("Try again? [Y]es / [o]ther model / [n]o: ").strip().lower()
        if response in ('', 'y', 'yes'):
            return True
        if response in ('o', 'other') and choose_model(ai_service):
            return True
        if response in ('n', 'no'):
            return False


def choose_model(ai_service: AIService) -> bool:
    """Lets the user switch to another model for the rest of the run. False if they cancel or it can't be listed."""
    try:
        models = [m for m in ai_service.available_models() if m != ai_service.model_name]
    except AIError as e:
        print(f"Could not list the models: {e}")
        return False
    if not models:
        print("No other models available.")
        return False

    for number, model in enumerate(models, start=1):
        print(f"  {number}. {model.removeprefix('models/')}")
    while True:
        response = input("Model number (Enter to cancel): ").strip()
        if not response:
            return False
        if response.isdigit() and 1 <= int(response) <= len(models):
            ai_service.model_name = models[int(response) - 1]
            return True


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

        result = self.get_entries(folders)
        if result is None:
            return
        entries, metadata = result

        renamable = drop_conflicts(entries, self.root_folder)
        approved, metadata_to_save = self.confirmer.confirm(entries, renamable, metadata)

        for series, item in metadata_to_save.items():
            self.save_metadata(series, item)
        print()
        for entry in approved:
            self.rename_folder(entry.original, entry.new_name)
        self.logger.print_completion_status(self.metadata_cache.path)

    def get_entries(self, folders: list[str]) -> tuple[list[Entry], dict[str, dict]] | None:
        """Asks the AI, offering to try again on temporary errors. Returns None if there is nothing to rename."""
        while True:
            try:
                return self.ai_request.get_entries(folders, self.root_folder, self.country)
            except AIError as e:
                print(f"Error getting a response from the AI: {e}")
                if not (e.retryable and ask_retry(self.ai_request.ai_service)):
                    return None
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing AI response: {e}")
                return None

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

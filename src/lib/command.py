import json
import os

from .ai_service import AIService
from .logger import Logger


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
            folders = [item for item in items if os.path.isdir(os.path.join(self.root_folder, item))]
            self.logger.log_folders(folders, self.root_folder)

            if not folders:
                return

            rename_pairs = self.get_rename_pairs(folders)

            try:
                for current_name, new_name in rename_pairs:
                    self.rename_folder(current_name, new_name)
                self.logger.print_completion_status()
            except json.JSONDecodeError as e:
                print(f"Error parsing AI response as JSON: {e}")
                print("Please check the response format and try again.")
            except Exception as e:
                print(f"Error during folder renaming: {e}")

        except OSError as e:
            print(f"Error accessing {self.root_folder}: {e}")

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
            os.rename(original_path, new_path)
            print(f"Renamed: '{current_name}' -> '{new_name}'")
            self.logger.increment_successful_renames()
        else:
            print(f"Not renamed: '{current_name}'")

    def get_rename_pairs(self, folders: list[str]) -> list[tuple[str, str]]:
        prompt = self.get_prompt("\n".join(folders))

        response = self.ai_service.ask(prompt)

        print("\n--- AI Response ---")
        print(response)
        print("-------------------------\n")

        return self.parse_rename_pairs_response(response)

    def get_prompt(self, folder_list_str):
        return f"""Here is a list of folder names:

    {folder_list_str}

    For each folder name, reformat it as '{{title}} v{{two-digit number}}' if it contains a version number, 
    or just '{{title}}' if there is no volume number. Remove any other information such as author name.
    Titles may have two parts, such as "First part - Second part".
    Numbers may also be part of the title, if they are at the beginning or middle.
    Return your answer as a JSON array of pairs [original_name, new_name]. Make sure all pairs are valid.
    """

    @staticmethod
    def parse_rename_pairs_response(response: str) -> list[tuple[str, str]]:
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON array found in the response")
        json_str = response[json_start:json_end]
        rename_pairs = json.loads(json_str)
        return rename_pairs

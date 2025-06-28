import os
import json
from .ai_service import AIService


class Command:
    def __init__(self, root_folder: str):
        if not os.path.isdir(root_folder):
            raise ValueError(f"The provided path is not a valid directory: {root_folder}")
        self.root_folder = root_folder
        print(f"Command initialized for folder: {self.root_folder}")

        self.ai_service = AIService()

    def execute(self):
        print(f"\nExecuting command on: {self.root_folder}")
        self.rename_folders()


    def rename_folders(self):
        try:
            items = os.listdir(self.root_folder)
            folders = [item for item in items if os.path.isdir(os.path.join(self.root_folder, item))]

            if not folders:
                print("No folders found to rename.")
                return

            print(f"Found {len(folders)} folders in {self.root_folder}")
            for folder in folders:
                print(f" - {folder}")

            rename_pairs = self.get_rename_pairs(folders)

            try:
                successful_renames = 0
                for original, new_name in rename_pairs:
                    if original == new_name:
                        print(f"No change needed for: {original}")
                        continue

                    original_path = os.path.join(self.root_folder, original)
                    if not os.path.exists(original_path):
                        print(f"Warning: Original folder '{original}' not found, skipping.")
                        continue

                    new_path = os.path.join(self.root_folder, new_name)
                    os.rename(original_path, new_path)
                    print(f"Renamed: '{original}' -> '{new_name}'")
                    successful_renames += 1

                print(f"\nCompleted: {successful_renames} folders renamed successfully.")

            except json.JSONDecodeError as e:
                print(f"Error parsing AI response as JSON: {e}")
                print("Please check the response format and try again.")
            except Exception as e:
                print(f"Error during folder renaming: {e}")

        except OSError as e:
            print(f"Error accessing {self.root_folder}: {e}")

    def get_rename_pairs(self, folders: list[str]) -> list[tuple[str, str]]:
        folder_list_str = "\n".join(folders)
        prompt = f"""Here is a list of folder names:

    {folder_list_str}

    For each folder name, reformat it as '{{title}} v{{two-digit number}}' if it contains a version number, 
    or just '{{title}}' if there is no volume number. Remove any other information.
    Return your answer as a JSON array of pairs [original_name, new_name]. Make sure all pairs are valid."""

        response = self.ai_service.ask(prompt)

        print("\n--- AI Response ---")
        print(response)
        print("-------------------------\n")

        return self.parse_rename_pairs_response(response)

    @staticmethod
    def parse_rename_pairs_response(response: str) -> list[tuple[str, str]]:
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON array found in the response")
        json_str = response[json_start:json_end]
        rename_pairs = json.loads(json_str)
        return rename_pairs

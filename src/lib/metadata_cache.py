import json
import os

FILE_NAME = "comic_metadata.json"


class MetadataCache:
    """Series metadata confirmed by the user, keyed by series name. Stored at the root of the comics folder."""

    def __init__(self, root_folder: str):
        self.path = os.path.join(root_folder, FILE_NAME)
        self.data = self._load()

    def get(self, series: str) -> dict | None:
        return self.data.get(series)

    def set(self, series: str, metadata: dict):
        self.data[series] = metadata
        self._save()

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        # Fail instead of starting empty, so a hand-editing mistake doesn't get the file overwritten
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as e:
            raise ValueError(f"Could not read {self.path}: {e}") from e
        if not isinstance(data, dict):
            raise ValueError(f"Could not read {self.path}: expected a JSON object keyed by series name")
        return data

    def _save(self):
        temp_path = self.path + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as file:
            json.dump(dict(sorted(self.data.items())), file, indent=2, ensure_ascii=False)
            file.write('\n')
        os.replace(temp_path, self.path)

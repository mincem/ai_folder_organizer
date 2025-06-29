import json
import os

DEFAULT_CACHE_FILE = os.path.join("cache", "gemini_cache.json")


class AICache:
    def __init__(self, cache_file=DEFAULT_CACHE_FILE):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache[key] = value
        self._save_cache()

    def __contains__(self, key):
        return key in self.cache

    def _load_cache(self):
        try:
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading cache: {e}")
            return {}

    def _save_cache(self) -> None:
        try:
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

            with open(self.cache_file, 'w', encoding='utf-8') as file:
                json.dump(self.cache, file, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")

import json
import os
from datetime import datetime

from .ai_client import AIResponse

DEFAULT_LOG_DIR = "logs"


class Logger:
    def __init__(self, log_dir: str = DEFAULT_LOG_DIR):
        self.log_dir = log_dir
        self.successful_renames = 0
        self.saved_metadata = 0

    def increment_successful_renames(self):
        self.successful_renames += 1

    def increment_saved_metadata(self):
        self.saved_metadata += 1

    def log_folders(self, folders, root_folder):
        if folders:
            print(f"{root_folder}: {len(folders)} folders")
        else:
            print(f"{root_folder}: no folders found to rename.")

    def save_ai_log(self, prompt: str, response: AIResponse, model: str, seconds: float,
                    root_folder: str, country: str = None) -> str | None:
        """Writes one file per run with the prompt and response, for debugging. Returns its path."""
        now = datetime.now()
        if response.cached:
            source = "cached response (no request sent)"
        else:
            source = f"{seconds:.1f}s" + (f", {response.tokens} tokens" if response.tokens else '')
        lines = [
            f"# AI request {now:%Y-%m-%d %H:%M:%S}",
            "",
            f"- Folder: {root_folder}",
            f"- Country: {country or '-'}",
            f"- Model: {model}",
            f"- Response: {source}",
            *self.response_details(response),
            "",
            "## Prompt",
            "",
            prompt,
            "",
            "## Response",
            "",
            "```json",
            self.pretty_json(response.text),
            "```",
            "",
        ]
        path = os.path.join(self.log_dir, f"{now:%Y-%m-%d_%H-%M-%S}.md")
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        except OSError as e:
            print(f"Error saving the AI log: {e}")
            return None
        return path

    @staticmethod
    def response_details(response: AIResponse) -> list[str]:
        if response.cached:
            return []
        tokens = {'prompt': response.prompt_tokens, 'output': response.output_tokens,
                  'thinking': response.thinking_tokens}
        return [
            f"- Model version: {response.model_version or '-'}",
            f"- Finish reason: {response.finish_reason or '-'}",
            *([f"- Block reason: {response.block_reason}"] if response.block_reason else []),
            f"- Tokens: {', '.join(f'{name} {count or 0}' for name, count in tokens.items())}",
        ]

    @staticmethod
    def pretty_json(text: str) -> str:
        # The raw text is kept when it isn't valid JSON, since that's when the log is needed most
        try:
            return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return text

    def print_completion_status(self, metadata_path: str):
        print(f"\nCompleted: {self.successful_renames} folders renamed successfully.")
        if self.saved_metadata:
            print(f"Saved metadata for {self.saved_metadata} series to {metadata_path}")

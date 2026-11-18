import json

import pytest

from lib.ai_client import AIClient, AIResponse
from lib.ai_service import AIService
from lib.command import Command
from lib.logger import Logger
from lib.metadata_cache import MetadataCache


class FakeAIClient(AIClient):
    """Returns a canned response and records the prompts it was asked."""
    model_name = "models/fake-model"

    def __init__(self, response: dict | str = None, cached: bool = False):
        self.response = response
        self.cached = cached
        self.prompts = []

    def is_cached(self, prompt: str) -> bool:
        return self.cached

    def ask(self, prompt: str, response_schema: dict = None) -> AIResponse:
        self.prompts.append(prompt)
        text = self.response if isinstance(self.response, str) else json.dumps(self.response)
        return AIResponse(text=text, cached=self.cached)


@pytest.fixture
def comics_dir(tmp_path):
    """An empty folder to hold the comic folders; logs go to a separate folder."""
    directory = tmp_path / "comics"
    directory.mkdir()
    return directory


@pytest.fixture
def make_command(comics_dir, tmp_path):
    """Builds a Command over comics_dir that talks to a FakeAIClient with the given response."""
    def make(response=None, country=None, cached=False):
        client = FakeAIClient(response, cached)
        command = Command(str(comics_dir), country, AIService(client), MetadataCache(str(comics_dir)),
                          Logger(log_dir=str(tmp_path / "logs")))
        command.fake_client = client
        return command
    return make

import json

import pytest

from lib.ai_client import AIClient, AIResponse
from lib.ai_service import AIService
from lib.command import Command
from lib.logger import Logger
from lib.metadata_cache import MetadataCache


class FakeAIClient(AIClient):
    """Returns a canned response (or raises it, if it's an exception) and records the prompts it was asked."""
    model_name = "models/fake-model"

    def __init__(self, response: dict | str = None, cached: bool = False):
        self.response = response
        self.cached = cached
        self.prompts = []

    def is_cached(self, prompt: str) -> bool:
        return self.cached

    def ask(self, prompt: str, response_schema: dict = None) -> AIResponse:
        self.prompts.append(prompt)
        if isinstance(self.response, Exception):
            raise self.response
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
    def make(response: dict | str | Exception = None, country=None, cached=False):
        client = FakeAIClient(response, cached)
        command = Command(str(comics_dir), country, AIService(client), MetadataCache(str(comics_dir)),
                          Logger(log_dir=str(tmp_path / "logs")))
        command.fake_client = client
        return command
    return make


@pytest.fixture
def answers(monkeypatch):
    """Scripts the user's answers to input(). Returns the prompts shown, to check what was asked.

    Asking more questions than there are answers fails the test, so call it with no answers
    to check that nothing is asked."""
    prompts = []

    def set_answers(*responses):
        pending = list(responses)

        def fake_input(prompt=''):
            prompts.append(prompt)
            if not pending:
                raise AssertionError(f"Unexpected question: {prompt!r}")
            return pending.pop(0)

        monkeypatch.setattr('builtins.input', fake_input)
        return prompts
    return set_answers

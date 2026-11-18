from abc import ABC, abstractmethod
from dataclasses import dataclass


class AIError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        # True when the same request may work later (e.g. the model is overloaded), so it's worth offering a retry
        self.retryable = retryable


@dataclass
class AIResponse:
    text: str
    cached: bool = False
    tokens: int | None = None
    # Only set for new requests, the cache keeps just the text
    finish_reason: str | None = None
    block_reason: str | None = None
    model_version: str | None = None
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None

    @property
    def problem(self) -> str | None:
        """Why the response may be incomplete, or None if it finished normally."""
        if self.block_reason:
            return f"the prompt was blocked ({self.block_reason})"
        if self.finish_reason and self.finish_reason != 'STOP':
            if self.finish_reason == 'MAX_TOKENS':
                return "the response was cut off (MAX_TOKENS)"
            return f"the response stopped early ({self.finish_reason})"
        return None


class AIClient(ABC):
    model_name: str = ''

    @abstractmethod
    def is_cached(self, prompt: str) -> bool:
        pass

    @abstractmethod
    def ask(self, prompt: str, response_schema: dict = None) -> AIResponse:
        pass

    @abstractmethod
    def available_models(self) -> list[str]:
        """Names of the models that can be set as model_name. Raises AIError if they can't be listed."""

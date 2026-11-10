from abc import ABC, abstractmethod


class AIError(Exception):
    pass


class AIClient(ABC):

    @abstractmethod
    def ask(self, prompt: str, response_schema: dict = None) -> str:
        pass

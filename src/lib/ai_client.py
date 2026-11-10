from abc import ABC, abstractmethod


class AIClient(ABC):

    @abstractmethod
    def ask(self, prompt: str, response_schema: dict = None) -> str:
        pass

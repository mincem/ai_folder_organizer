from abc import ABC, abstractmethod


class AIClient(ABC):

    @abstractmethod
    def ask(self, prompt: str) -> str:
        pass

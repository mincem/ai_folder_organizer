from .ai_client import AIClient
from .gemini_client import GeminiClient


class AIService:
    def __init__(self, ai_client: AIClient = None):
        self.ai_client = ai_client or GeminiClient()

    def ask(self, prompt: str) -> str:
        return self.ai_client.ask(prompt)

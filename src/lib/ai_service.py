from .ai_client import AIClient, AIResponse
from .gemini_client import GeminiClient


class AIService:
    def __init__(self, ai_client: AIClient = None):
        self.ai_client = ai_client or GeminiClient()

    @property
    def model_name(self) -> str:
        return self.ai_client.model_name

    @model_name.setter
    def model_name(self, name: str):
        self.ai_client.model_name = name

    def available_models(self) -> list[str]:
        return self.ai_client.available_models()

    def is_cached(self, prompt: str) -> bool:
        return self.ai_client.is_cached(prompt)

    def ask(self, prompt: str, response_schema: dict = None) -> AIResponse:
        return self.ai_client.ask(prompt, response_schema)

import os
from google import genai
from google.genai import errors, types

from .ai_cache import AICache
from .ai_client import AIClient

DEFAULT_MODEL = "models/gemini-3.6-flash"


def create_gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found.")
    return genai.Client(api_key=api_key)


def list_generation_models(client: genai.Client) -> list[str]:
    return [m.name for m in client.models.list()
            if 'generateContent' in (m.supported_actions or [])]


class GeminiClient(AIClient):
    def __init__(self):
        self.cache = AICache()
        self.model_name = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        try:
            self.client = create_gemini_client()
            print(f"Gemini API configured successfully (model: {self.model_name}).")
        except Exception as e:
            print(f"Error configuring Gemini API: {e}")
            self.client = None

    def ask(self, prompt: str, response_schema: dict = None) -> str:
        if not self.client:
            return "Cannot ask Gemini, the client was not initialized."

        if prompt in self.cache:
            print("\n--- Using cached response ---")
            print(f"Prompt: {prompt}")
            return self.cache.get(prompt)

        print("\n--- Sending prompt to Gemini ---")
        print(f"Prompt: {prompt}")
        try:
            config = None
            if response_schema:
                config = types.GenerateContentConfig(response_mime_type="application/json",
                                                     response_json_schema=response_schema)
            response = self.client.models.generate_content(model=self.model_name, contents=prompt, config=config)
            response_text = response.text

            self.cache.set(prompt, response_text)
            return response_text
        except errors.ClientError as e:
            if e.code != 404:
                return f"An error occurred while calling the Gemini API: {e}"
            return (f"Gemini model '{self.model_name}' was not found. "
                    f"Set GEMINI_MODEL to one of: {', '.join(list_generation_models(self.client))}")
        except Exception as e:
            return f"An error occurred while calling the Gemini API: {e}"

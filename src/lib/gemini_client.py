import os
import google.generativeai as genai

from .ai_cache import AICache
from .ai_client import AIClient


class GeminiClient(AIClient):
    def __init__(self):
        self.cache = AICache()
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not found.")
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
            print("Gemini API configured successfully.")
        except Exception as e:
            print(f"Error configuring Gemini API: {e}")
            self.model = None

    def ask(self, prompt: str) -> str:
        if not self.model:
            return "Cannot ask Gemini, the model was not initialized."

        if prompt in self.cache:
            print("\n--- Using cached response ---")
            print(f"Prompt: {prompt}")
            return self.cache.get(prompt)

        print("\n--- Sending prompt to Gemini ---")
        print(f"Prompt: {prompt}")
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text

            self.cache.set(prompt, response_text)
            return response_text
        except Exception as e:
            return f"An error occurred while calling the Gemini API: {e}"

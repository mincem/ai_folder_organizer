import os
from google import genai
from google.genai import errors, types

from .ai_cache import AICache
from .ai_client import AIClient, AIError, AIResponse

DEFAULT_MODEL = "models/gemini-3.6-flash"


def create_gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found.")
    return genai.Client(api_key=api_key)


def list_generation_models(client: genai.Client) -> list[str]:
    return [m.name for m in client.models.list()
            if 'generateContent' in (m.supported_actions or [])]


def to_ai_error(error: errors.APIError) -> AIError:
    """Turns an API error into a short message, e.g. "503 UNAVAILABLE: This model is currently experiencing...".

    The SDK reads code, status and message from the error JSON; message can be None (e.g. a non-JSON body),
    and then the full error is shown instead."""
    if error.message:
        message = f"Gemini API error {error.code} {error.status or ''}".rstrip() + f": {error.message}"
    else:
        message = f"Gemini API error: {error}"
    # Too many requests (429) and server errors (5xx) are usually temporary
    retryable = error.code == 429 or (error.code or 0) >= 500
    return AIError(message, retryable=retryable)


class GeminiClient(AIClient):
    def __init__(self):
        self.cache = AICache()
        self.model_name = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        try:
            self.client = create_gemini_client()
        except Exception as e:
            print(f"Error configuring Gemini API: {e}")
            self.client = None

    def is_cached(self, prompt: str) -> bool:
        return prompt in self.cache

    def ask(self, prompt: str, response_schema: dict = None) -> AIResponse:
        if not self.client:
            raise AIError("Cannot ask Gemini, the client was not initialized.")

        if self.is_cached(prompt):
            return AIResponse(self.cache.get(prompt), cached=True)

        try:
            config = None
            if response_schema:
                config = types.GenerateContentConfig(response_mime_type="application/json",
                                                     response_json_schema=response_schema)
            response = self.client.models.generate_content(model=self.model_name, contents=prompt, config=config)
            result = self.to_ai_response(response)
            # An incomplete response would come back from the cache on every retry
            if not result.problem:
                self.cache.set(prompt, result.text)
            return result
        except errors.APIError as e:
            if e.code == 404:
                raise AIError(f"Gemini model '{self.model_name}' was not found. "
                              f"Set GEMINI_MODEL to one of: {', '.join(list_generation_models(self.client))}") from e
            raise to_ai_error(e) from e
        except Exception as e:
            raise AIError(f"An error occurred while calling the Gemini API: {e}") from e

    def available_models(self) -> list[str]:
        if not self.client:
            raise AIError("Cannot list Gemini models, the client was not initialized.")
        try:
            return list_generation_models(self.client)
        except errors.APIError as e:
            raise to_ai_error(e) from e
        except Exception as e:
            raise AIError(f"Could not list the Gemini models: {e}") from e

    @staticmethod
    def to_ai_response(response: types.GenerateContentResponse) -> AIResponse:
        usage = response.usage_metadata or types.GenerateContentResponseUsageMetadata()
        candidate = response.candidates[0] if response.candidates else None
        feedback = response.prompt_feedback
        return AIResponse(
            # Blocked responses have no text; empty text then fails parsing as usual
            response.text or '',
            tokens=usage.total_token_count,
            finish_reason=candidate.finish_reason.name if candidate and candidate.finish_reason else None,
            block_reason=feedback.block_reason.name if feedback and feedback.block_reason else None,
            model_version=response.model_version,
            prompt_tokens=usage.prompt_token_count,
            output_tokens=usage.candidates_token_count,
            thinking_tokens=usage.thoughts_token_count,
        )

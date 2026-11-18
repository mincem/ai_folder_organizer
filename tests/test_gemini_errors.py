"""Turning Gemini API errors into short, readable AIErrors."""
from google.genai import errors

from lib.gemini_client import to_ai_error


def api_error(cls, code, response_json):
    return cls(code, response_json)


def test_server_error_shows_message_and_is_retryable():
    error = to_ai_error(api_error(errors.ServerError, 503, {
        "error": {"code": 503, "message": "Some temporary problem.", "status": "UNAVAILABLE"}}))

    assert str(error) == "Gemini API error 503 UNAVAILABLE: Some temporary problem."
    assert error.retryable


def test_too_many_requests_is_retryable():
    error = to_ai_error(api_error(errors.ClientError, 429, {
        "error": {"code": 429, "message": "Some quota message.", "status": "RESOURCE_EXHAUSTED"}}))

    assert error.retryable


def test_bad_request_is_not_retryable():
    error = to_ai_error(api_error(errors.ClientError, 400, {
        "error": {"code": 400, "message": "Some bad request.", "status": "INVALID_ARGUMENT"}}))

    assert str(error) == "Gemini API error 400 INVALID_ARGUMENT: Some bad request."
    assert not error.retryable


def test_error_without_message_falls_back_to_full_error():
    error = to_ai_error(api_error(errors.ServerError, 502, {"unexpected": "shape"}))

    assert str(error).startswith("Gemini API error: 502")
    assert "unexpected" in str(error)
    assert error.retryable

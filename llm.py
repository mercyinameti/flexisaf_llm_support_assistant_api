# llm.py
# This file is the only part of the app that talks to Gemini.

import os  # Lets us read environment variables such as GEMINI_API_KEY

import httpx  # The library the SDK uses to send requests. Its errors cover timeouts and connections.
from dotenv import load_dotenv  # Reads the .env file into environment variables
from google import genai  # The official Gemini SDK, the same one from Week 3
from google.genai import errors  # The SDK's error type, which includes the status code
from google.genai import types  # Holds the configuration options, such as the timeout
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential  # The retry tools

load_dotenv()  # Loads GEMINI_API_KEY from .env. Must run before we read the key.

MAIN_MODEL = "gemini-3.5-flash-lite"  # The first model we try
BACKUP_MODEL = "gemini-3.1-flash-lite"  # The backup model

# The client is the SDK object that sends requests to Gemini.
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=20000),  # Give up after 20 seconds (20000 milliseconds)
)

ATTEMPTS = {"count": 0}  # How many times ask_model has run for the current request


def is_temporary(error):
    # Return True only for errors that might succeed on a second try.
    if isinstance(error, httpx.TransportError):  # Timeouts and connection problems
        return True
    if isinstance(error, errors.APIError):
        return error.code == 429 or error.code >= 500  # Rate limit, or the server is busy
    return False  # Everything else, such as a wrong key, fails straight away


@retry(  # The decorator sits directly above the function it wraps
    retry=retry_if_exception(is_temporary),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,  # After the last try, raise the original error
)
def ask_model(question: str, model: str):
    # This body runs once per attempt, so counting here counts every attempt.
    ATTEMPTS["count"] += 1
    # Return the whole response, so the caller can read the text and the token counts.
    return client.models.generate_content(
        model=model,
        contents=question,
    )


def ask_with_fallback(question: str):
    # Returns (response, model name, total attempts across both models).
    ATTEMPTS["count"] = 0  # Start counting for this request
    try:
        response = ask_model(question, MAIN_MODEL)
        return response, MAIN_MODEL, ATTEMPTS["count"]
    except Exception as error:
        if not is_temporary(error):
            raise
        response = ask_model(question, BACKUP_MODEL)  # The count keeps going across both models
        return response, BACKUP_MODEL, ATTEMPTS["count"]
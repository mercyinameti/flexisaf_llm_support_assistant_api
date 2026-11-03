# main.py
# This file defines the routes (addresses) the server responds to.

import json  # Converts a record to text for the log file
import time  # Measures how long a request takes
from datetime import datetime, timezone  # Adds a timestamp to each log line

from fastapi import FastAPI, HTTPException, Request  # Request gives access to per-request storage
from google.genai import errors  # The SDK's error type, which holds the status code
from llm import ask_with_fallback, ATTEMPTS # Calls Gemini, with the backup model if needed, ATTEMPTS holds the count for the current request
from models import AskRequest, AskResponse  # The request and reply rules from models.py

app = FastAPI()  # Creates the application. Uvicorn runs this object.

LOG_FILE = "logs.jsonl"  # One JSON record per line, written to this file


def write_log(record: dict):
    # Add the time, then append the record as one line in the log file.
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


@app.get("/")  # GET = the client is asking for information. This route is the health check.
def home():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, http_request: Request):
    try:
        # Returns the response, the model that answered, and the total attempts made.
        response, model_used, attempts = ask_with_fallback(request.question)
    except errors.APIError as error:
        http_request.state.attempts = ATTEMPTS["count"]  # Record attempts even when the request fails
        if error.code == 429:
            raise HTTPException(
                status_code=429,
                detail="Too many requests right now. Please wait a minute and try again.",
            )
        raise HTTPException(
            status_code=503,
            detail="The model is not available right now. Please try again shortly.",
        )
    except Exception as error:
        # Record the real error for us. The client still gets the safe message.
        http_request.state.attempts = ATTEMPTS["count"]  # Record attempts even when the request fails
        write_log({"error": f"{type(error).__name__}: {error}"})
        raise HTTPException(
            status_code=503,
            detail="The model is not available right now. Please try again shortly.",
        )

    # Store the details on the request, so the logging middleware can record them.
    http_request.state.model = model_used
    http_request.state.attempts = attempts
    usage = response.usage_metadata  # Token counts reported by Gemini, or None
    http_request.state.tokens = usage.total_token_count if usage else None
    http_request.state.input_tokens = usage.prompt_token_count if usage else None
    http_request.state.output_tokens = (usage.total_token_count - usage.prompt_token_count) if usage else None

    return {"question": request.question, "answer": response.text}


@app.middleware("http")
async def log_every_request(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000)
    write_log({
        "path": request.url.path,
        "status": response.status_code,
        "response_ms": elapsed_ms,
        # Returns None for requests that never reached the model, such as /docs.
        "model": getattr(request.state, "model", None),
        "tokens": getattr(request.state, "tokens", None),
        "attempts": getattr(request.state, "attempts", None),
        "input_tokens": getattr(request.state, "input_tokens", None),
        "output_tokens": getattr(request.state, "output_tokens", None),
    })
    return response
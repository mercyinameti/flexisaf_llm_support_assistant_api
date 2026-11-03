# LLM Support Assistant API

A FastAPI server that accepts a question, sends it to Google's Gemini model, and returns the answer. It validates requests, retries temporary failures, falls back to a backup model, logs every request, and records token counts for cost estimates.

## Setup

Requires Python 3.12. Python 3.14 does not yet have compatible `pydantic-core` builds on Windows.

```
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a file named `.env` in the project folder containing your key:

```
GEMINI_API_KEY=your-key-here
```

Never commit `.env`. It is listed in `.gitignore`. Get a key from Google AI Studio.

## Running the server

```
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs to try the API in the browser.

`.env` is read only when the server starts, so restart the server after changing it.

## Usage

Send a POST request to `/ask` with a JSON body:

```json
{"question": "Summarise in one sentence why a support assistant needs logging."}
```

A successful reply (200):

```json
{"question": "...", "answer": "..."}
```

Run the sample client, which sends one good request and one bad one:

```
python client.py
```

## Errors

| Status | Meaning |
|---|---|
| 422 | The request is invalid: empty, missing the field, malformed JSON, or over 2,000 characters |
| 429 | Gemini's quota is used up. Wait a minute and try again |
| 503 | The model is unavailable: Gemini could not be reached, the key is wrong, or all attempts timed out |

See `FAILURE_EVIDENCE.md` for the tests behind each code.

## How it works

- **Validation:** `models.py` checks each request before any model call.
- **Timeout:** each call to Gemini gives up after 20 seconds.
- **Retries:** temporary failures (timeouts, connection errors, 429, 5xx) are retried up to three times with increasing waits. Wrong keys and bad requests fail at once.
- **Fallback:** if the main model fails temporarily, the backup model is tried.
- **Logging:** every request is written to `logs.jsonl` with the model, attempts, tokens, and response time.

## Cost

`make_cost_report.py` reads `logs.jsonl` and writes `cost_report.csv`.

- The free tier costs nothing, so the report also shows the paid-rate estimate.
- Paid rates (USD per 1,000,000 tokens), checked 3 November 2026 at the Gemini Developer API pricing page:
  - `gemini-3.5-flash-lite`: input $0.30, output $2.50
  - `gemini-3.1-flash-lite`: input $0.25 (text), output $1.50
- Output tokens include thinking tokens, which Gemini bills as output.
- Requests logged before token counts were recorded have no cost estimate.

## Limits

- The attempt counter is shared across all requests. If two requests run at the same time, their attempt counts can mix. Fix this before handling concurrent traffic.
- No system instruction is set, so the model answers as a general assistant rather than a support agent.
- Streaming responses are not supported.
- The free tier has daily request limits per model.

## Files

- `main.py`: routes, error handling, and logging
- `llm.py`: the only file that calls Gemini, with retries and fallback
- `models.py`: request and reply rules
- `client.py`: sample client
- `failure_tests.py`: sends bad requests on purpose
- `make_cost_report.py`: builds the cost report
- `cost_report.csv`: the cost spreadsheet, generated from the log
- `requirements.txt`: pinned package versions
- `.env.example`: shows the key setting without a real key
- `.gitignore`: keeps `.env`, `.venv/`, `__pycache__/`, and `logs.jsonl` out of the repo
- `FAILURE_EVIDENCE.md`: results of each failure test
- `BUILD_LOG.md`: the step-by-step record of how the project was built
# Failure Evidence

Each test was run against the live server (`uvicorn main:app --reload`) on 3 November 2026. "Attempts" and "Model" come from `logs.jsonl`.

## Test results

| # | Scenario | How it was triggered | Status | Client message | Attempts | Model | Gemini called? |
|---|---|---|---|---|---|---|---|
| 1 | Successful request | `client.py`, normal question | 200 | Answer returned | 1 | gemini-3.5-flash-lite | Yes |
| 2 | Empty question | `{"question": ""}` | 422 | `String should have at least 1 character` | none | none | No |
| 3 | Missing question field | `{"text": "hello"}` | 422 | Field `question` required | none | none | No |
| 4 | Malformed JSON | `{"question" "hello"}` (missing colon) | 422 | JSON parse error | none | none | No |
| 5 | Question too long | 2,001 characters | 422 | `String should have at most 2000 characters` | none | none | No |
| 6 | Wrong API key | Key in `.env` altered, server restarted | 503 | `The model is not available right now. Please try again shortly.` | 1 | none | Yes, rejected |
| 7 | Forced timeout | `timeout=1` in `llm.py` | 503 | `The model is not available right now. Please try again shortly.` | 6 | none | Yes, timed out |
| 8 | Rate limit | Not triggered | 429 | `Too many requests right now. Please wait a minute and try again.` | n/a | n/a | n/a |

## Failure-state reference

| Status | Cause | What the client sees | What is logged |
|---|---|---|---|
| 422 | The request breaks a rule in `models.py`, or the JSON is malformed | FastAPI's validation message | `status`, `model: null`, no attempts |
| 429 | Gemini's quota is used up | Wait-and-retry message | `status`, `model: null`, `attempts` |
| 503 | Gemini is unreachable, the key is wrong, or every attempt timed out | Safe "not available" message | Full error text in `error` field, plus `attempts` |

Real error details never reach the client. They are written only to `logs.jsonl`.

## Notes

- A 422 never calls Gemini, so it costs nothing and uses no tokens.
- A 503 after a wrong key stops after one attempt, because authentication errors are not retried.
- A 503 after a timeout makes six attempts: three on the main model, then three on the backup model.
- Test 8 is not tested. Quota has not run out.


## Log evidence

These lines were copied from `logs.jsonl`. The file itself is kept out of the repo because it holds user questions.

Successful request (200):

```json
{"path": "/ask", "status": 200, "response_ms": 1258, "model": "gemini-3.5-flash-lite", "tokens": 39, "attempts": 1, "input_tokens": 13, "output_tokens": 26, "timestamp": "2026-11-03T09:53:13.973989+00:00"}
```

Validation failure (422, Gemini not called):

```json
{"path": "/ask", "status": 422, "response_ms": 1, "model": null, "tokens": null, "attempts": null, "input_tokens": null, "output_tokens": null, "timestamp": "2026-11-03T09:53:14.460124+00:00"}
```

Wrong API key (503, 1 attempt):

```json
{"path": "/ask", "status": 503, "response_ms": 601, "model": null, "tokens": null, "attempts": 1, "input_tokens": null, "output_tokens": null, "timestamp": "2026-11-03T09:55:47.351117+00:00"}
```

Forced timeout (503, 6 attempts). The error line comes first, then the request line:

```json
{"error": "ConnectTimeout: timed out", "timestamp": "2026-11-03T10:06:14.155274+00:00"}
{"path": "/ask", "status": 503, "response_ms": 6131, "model": null, "tokens": null, "attempts": 6, "input_tokens": null, "output_tokens": null, "timestamp": "2026-11-03T10:06:14.155274+00:00"}
```

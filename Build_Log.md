# Build Log: Week 4

## Step 1: Project folder
- What: created `llm-support-assistant-api` and opened it in VS Code.
- Why: this folder is the GitHub repository. Everything in it can be pushed.

## Step 2: Python 3.12
- What: installed Python 3.12.10 alongside 3.14.
- Why: Pydantic 2 needs a compiled component (`pydantic-core`) that wasn't available for Python 3.14 on Windows. Python 3.12 has ready-made builds.

## Step 3: Virtual environment
- What: `py -3.12 -m venv .venv`, then activated it.
- Why: keeps this project's packages separate from other projects. `.venv/` must be in `.gitignore` and must not be pushed.

## Step 4: Install FastAPI and Uvicorn
- What: `pip install fastapi uvicorn`.
- Why: FastAPI builds the endpoints. Uvicorn runs them as a server. Both will be listed in `requirements.txt`.

## Step 5: First endpoint
- What: created `main.py` with a GET route at `/`.
- Why: checks that the server runs and that a request gets a reply.

## Step 6: Run the server
- What: `uvicorn main:app --reload`.
- Why: starts the server on your computer. `--reload` restarts it when the code changes. Ctrl+C stops it.

## Step 7: Request model
- What: created `models.py` with `AskRequest`, a question field with length rules.
- Why: the server checks every request before doing any work.

## Step 8: POST /ask endpoint
- What: added `POST /ask` in `main.py` that validates the request and returns a reply.
- Why: this is the endpoint other programs will call.

## Step 9: Gemini call
- What: created `llm.py` with `ask_model()`, and stored the key in `.env`.
- Why: the server, not the client, talks to Gemini. The key stays in `.env`, out of GitHub.
- Result: `POST /ask` returns a real answer. The network issue was a DNS problem, fixed by flushing the cache and reconnecting.

## Step 10: Timeout
- What: set a 10-second timeout on the Gemini client in `llm.py`.
- Why: a slow model shouldn't keep the server waiting forever.
- Test: 10 seconds is enough for a normal reply. A 1 ms timeout forced a failure.

## Step 11: Error handling
- What: `POST /ask` catches failures and returns 503 with a safe message.
- Why: the client gets a clear response, and no key or internal details are exposed.
- Test: the forced timeout returned 503. The normal request returned 200 after the change back.

## Step 12: Retries with exponential backoff
- What: added Tenacity to `ask_model()` with up to 3 attempts, waiting about 1s and then 2s between them.
- Why: temporary failures can succeed on a second try, and the growing wait avoids hammering a busy service.
- Test: with a forced 1 ms timeout, the 503 took about 7 to 8 seconds, consistent with three attempts. Normal replies still take 2 to 4 seconds.
- Limitation: every error is retried for now, including a wrong key. We'll limit retries to temporary errors next.

## Step 13: Retry only temporary errors
- What: `is_temporary()` in `llm.py` limits retries to timeouts, connection problems, 429, and 5xx errors. The retry decorator uses it, with `reraise=True`.
- Why: a wrong key or a bad request fails the same way every time, so retrying it wastes time.
- Test: a 1 ms timeout still took about 8 to 10 seconds (three attempts). A wrong key returned 503 in about 2 to 4 seconds (one attempt).
- Note: the client still sees the same generic 503 message for both. The specific cause is recorded in the logs, which we'll add later.

## Step 14: Fallback model
- What: `ask_with_fallback()` in `llm.py` tries `gemini-3.5-flash-lite` first and switches to `gemini-3.1-flash-lite` only on a temporary error. `ask_model()` now takes the model name as a parameter.
- Why: if the main model is unavailable, the server can still answer, using a model with its own quota.
- Test: with a forced 1 ms timeout, the 503 took about 18 seconds, which means both models were tried, three attempts each. A wrong key still fails without trying the backup.
- Note: the reply doesn't yet say which model answered. The logs will record that.

## Step 15: Timeout adjusted to 20 seconds
- What: changed the client timeout in `llm.py` from 10000 to 20000 milliseconds.
- Why: a normal reply took 8 to 10 seconds in testing, which was too close to the 10-second limit. A request that was almost ready was being treated as a timeout.
- Test: `hello` returns 200. The logs will show response times, so the final value can be checked against real data.

## Step 16: Request logging (part 1)
- What: a middleware in `main.py` writes one JSON line per request to `logs.jsonl` with the path, status, response time, and timestamp. The question text is not logged.
- Why: a record of every request, including rejected ones, so problems can be checked later.
- Test: `/ask` returned 200 in about 2.9 seconds, and an empty question returned 422 in 5 milliseconds, without calling the model.
- Next: add the model used, retry count, and token counts.

## Step 17: Request logging (part 2)
- What: `/ask` stores the model used and the token count on the request. The logging middleware writes them to `logs.jsonl`.
- Why: each record shows which model answered and how much it cost in tokens.
- Test: `hello` returned `gemini-3.5-flash-lite` with 11 tokens in 7.1 seconds. Duplicate log lines were traced to an old middleware, which was removed.
- Next: add the retry count, so slow requests like the 38.5-second one can be explained.

## Step 18: Attempt count in logs (done)
- What: `ask_model()` increments a counter on each run, and `ask_with_fallback()` reads it. The counter is written to `logs.jsonl` as `attempts`.
- Test: a normal request logged `"attempts": 1`.
- Note: earlier versions gave `0` on success and raised a `KeyError`, because they relied on tenacity's internal callbacks. Counting inside the function avoids both problems.
- Still to test: the forced-timeout run should log `"attempts": 6`.

## Step 19: Attempt count on failures
- What: the error handlers in `/ask` record the attempt count before raising the 503 or 429. The real error is written to the log, and the client still gets the safe message.
- Test: a normal request logged `"attempts": 1`. A forced timeout logged the `ConnectTimeout` error and `"attempts": 6`, showing three tries on each model.
- Note: the log has a `model` value only when a reply succeeds. A failed request shows `null`.

### Step 20: Split token counts in the log
Gemini reports total, prompt (input), and candidate (output) tokens. We logged input and output separately, because they have different prices. Output is calculated as total minus input, so it includes thinking tokens, which Gemini bills as output.
Concept: a log that records only totals can't tell you what something cost.

### Step 21: Cost report
Wrote `make_cost_report.py`. It reads `logs.jsonl`, applies paid rates per 1,000,000 tokens, and writes `cost_report.csv` with a totals row. Free-tier cost is $0.00 by definition.
Rates were taken from the Gemini Developer API pricing page on 3 November 2026: $0.30 input and $2.50 output for `gemini-3.5-flash-lite`, and $0.25 input and $1.50 output for `gemini-3.1-flash-lite`.
Concept: the script reads the log and writes a report, and it never changes the log.

### Step 22: Sample client
Wrote `client.py`, which sends a good request and an empty question. The first version printed the label "Successful request" even on a 503, so it looked like a pass when it was a failure. Fixed by giving each test an expected status and printing PASS or FAIL.
Concept: a test should compare the result with a stated expectation, not just print what happened.

### Step 23: Failure tests
Wrote `failure_tests.py`, which sends four bad requests: empty question, missing field, malformed JSON, and a 2,001-character question. All four returned 422. Each one was rejected by validation before the model was called.

### Step 24: Wrong key and forced timeout
These two tests need changes to `.env` or `llm.py`, so they are run by hand.
- Wrong key: the server still used the old key after editing `.env`. `.env` is read only at startup, so the server must be restarted. Result: 503, 1 attempt.
- Forced timeout: set `timeout=1`, restarted, ran the client. Result: 503, 6 attempts, which is three tries on the main model plus three on the backup. Then restored `timeout=20000`.

### Step 25: Evidence and docs
Recorded every test in `FAILURE_EVIDENCE.md`. Exported the API schema as `openapi.json` from `/openapi.json`. Pinned package versions in `requirements.txt` from `pip show`. Wrote `README.md`.

### Step 26: Git
Problems and fixes:
- The folder was inside a Git repo for the Windows user folder (`C:\Users\HP`). `git init` inside the project folder created a separate repo, so commits go to the project only.
- `git status` before the first commit confirmed `.env`, `logs.jsonl`, `.venv/`, and `__pycache__/` were not staged.
- The first remote address used the wrong repo name. Check the name in the URL before pushing.

Result: 16 files pushed to `main` at `mercyinameti/flexisaf_llm_support_assistant_api`.

### Lessons for a rebuild
- Put Gemini calls in one file (`llm.py`), so retries, timeouts, and fallback are in one place.
- Retry only temporary errors. A wrong key or bad request should fail at once.
- Count attempts with a plain counter inside the function that makes the call. Tenacity's statistics were unreliable for this.
- Validation errors (422) never reach the model, so they cost nothing.
- The attempt counter is global, so concurrent requests can mix their counts. This is listed as a limit in the README.

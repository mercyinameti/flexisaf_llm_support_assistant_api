# failure_tests.py
# Sends bad requests on purpose and prints how the server responds.

import httpx

BASE_URL = "http://127.0.0.1:8000"


def post_raw(label, content):
    # Send the raw text as the body, so malformed JSON reaches the server unchanged.
    print(f"\n--- {label} ---")
    response = httpx.post(
        f"{BASE_URL}/ask",
        content=content,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    print("Status:", response.status_code)
    print("Body:", response.text)


if __name__ == "__main__":
    post_raw("Empty question", '{"question": ""}')
    post_raw("Missing question field", '{"text": "hello"}')
    post_raw("Malformed JSON (missing colon)", '{"question" "hello"}')
    post_raw("Question too long (2001 characters)", '{"question": "' + "a" * 2001 + '"}')
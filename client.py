# client.py
# A sample client. It sends requests, compares each reply with the status we expect, and prints the result.

import httpx

BASE_URL = "http://127.0.0.1:8000"


def send(label, question, expected_status):
    # Send one question to /ask and check the status against what we expected.
    print(f"\n--- {label} ---")
    response = httpx.post(f"{BASE_URL}/ask", json={"question": question}, timeout=60)
    result = "PASS" if response.status_code == expected_status else "FAIL"
    print(f"Expected: {expected_status}  Got: {response.status_code}  Result: {result}")
    print("Body:", response.json())


if __name__ == "__main__":
    send("Successful request", "Summarise in one sentence why a support assistant needs logging.", 200)
    send("Failed request: empty question", "", 422)
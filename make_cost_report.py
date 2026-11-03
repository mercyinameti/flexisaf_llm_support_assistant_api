# make_cost_report.py
# Reads logs.jsonl and writes cost_report.csv with one row per /ask request.

import csv
import json

LOG_FILE = "logs.jsonl"
REPORT_FILE = "cost_report.csv"

# Paid-tier prices in USD per 1,000,000 tokens.
# Source: Gemini Developer API pricing page, checked 2026-11-03.
PRICES = {
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},  # text/image/video input rate
}


def estimate_cost(model, input_tokens, output_tokens):
    # Returns the estimated cost in dollars, or None if it can't be worked out.
    price = PRICES.get(model)
    if price is None or input_tokens is None or output_tokens is None:
        return None
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000


def main():
    rows = []
    with open(LOG_FILE, encoding="utf-8") as file:
        for line in file:
            record = json.loads(line)
            # Keep only requests that reached the model. Other routes and failed calls are skipped.
            if record.get("path") != "/ask" or record.get("model") is None:
                continue
            cost = estimate_cost(record["model"], record.get("input_tokens"), record.get("output_tokens"))
            rows.append({
                "timestamp": record.get("timestamp", ""),
                "model": record["model"],
                "attempts": record.get("attempts"),
                "input_tokens": record.get("input_tokens"),
                "output_tokens": record.get("output_tokens"),
                "estimated_cost_usd": f"{cost:.8f}" if cost is not None else "",
                "free_tier_cost_usd": "0.00",
            })

    # Totals row at the bottom
    total_in = sum(r["input_tokens"] or 0 for r in rows)
    total_out = sum(r["output_tokens"] or 0 for r in rows)
    total_cost = sum(float(r["estimated_cost_usd"] or 0) for r in rows)
    rows.append({
        "timestamp": "TOTAL",
        "model": "",
        "attempts": "",
        "input_tokens": total_in,
        "output_tokens": total_out,
        "estimated_cost_usd": f"{total_cost:.8f}",
        "free_tier_cost_usd": "0.00",
    })

    fieldnames = ["timestamp", "model", "attempts", "input_tokens", "output_tokens",
                  "estimated_cost_usd", "free_tier_cost_usd"]
    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows) - 1} requests to {REPORT_FILE}")
    print(f"Total estimated cost at paid rates: ${total_cost:.8f}")


if __name__ == "__main__":
    main()
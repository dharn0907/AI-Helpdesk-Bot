
import csv
import json
import re
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.llm_service import llm

DATASET_PATH = BASE_DIR / "data" / "business_intent_dataset.csv"
REPORT_PATH = BASE_DIR / "data" / "business_intent_audit.csv"

INTENTS = {
    "PRICING_ENQUIRY",
    "FEATURE_ENQUIRY",
    "PRODUCT_SERVICE_ENQUIRY",
    "COMPARISON_ENQUIRY",
    "AVAILABILITY_ENQUIRY",
    "BOOKING_ENQUIRY",
    "PURCHASE_ENQUIRY",
    "DEMO_ENQUIRY",
    "QUOTATION_ENQUIRY",
    "PARTNERSHIP_ENQUIRY",
    "OTHER_BUSINESS_ENQUIRY",
}

BATCH_SIZE = 25


def parse_response(content):
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )

    content = str(content).strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    return json.loads(content)


def audit_batch(batch, start_index):
    messages = [
        {
            "id": start_index + i,
            "text": row["text"],
            "current_label": row["intent"],
        }
        for i, row in enumerate(batch)
    ]

    prompt = f"""
You are auditing a business-intent classification dataset.

Classify each message into exactly one of these labels:

{json.dumps(sorted(INTENTS))}

Guidelines:
- PRICING_ENQUIRY: asks for a price, fee, cost or pricing information.
- FEATURE_ENQUIRY: asks what a product or service can do.
- PRODUCT_SERVICE_ENQUIRY: asks for information about a specific
  product, service, package or offering.
- COMPARISON_ENQUIRY: compares two or more offerings.
- AVAILABILITY_ENQUIRY: asks whether something is available or in stock.
- BOOKING_ENQUIRY: asks to create, change or manage a reservation,
  appointment or scheduled session.
- PURCHASE_ENQUIRY: expresses intent to buy or place an order.
- DEMO_ENQUIRY: asks for a demonstration, trial or product test.
- QUOTATION_ENQUIRY: requests a formal quote, estimate or proposal.
- PARTNERSHIP_ENQUIRY: asks about reselling, distribution, affiliates
  or business collaboration.
- OTHER_BUSINESS_ENQUIRY: other company-related questions that do not
  fit the categories above.

Important distinctions:
- A general price question is PRICING_ENQUIRY.
- A formal estimate or quotation request is QUOTATION_ENQUIRY.
- Asking whether something is available is not the same as booking it.
- Do not change a label just because another label is vaguely related.
- Mark unclear or insufficient messages as UNCERTAIN.
- Check for spelling errors and missing spaces.
- Preserve the original message text; do not rewrite it.

Review these records:
{json.dumps(messages, ensure_ascii=False)}

Return ONLY valid JSON:
{{
  "results": [
    {{
      "id": 0,
      "suggested_label": "PRICING_ENQUIRY",
      "quality": "OK",
      "reason": "Short explanation"
    }}
  ]
}}

quality must be one of: OK, WRONG_LABEL, UNCERTAIN, TEXT_ERROR.
"""

    response = llm.invoke(prompt)
    data = parse_response(response.content)
    return data["results"]


def main():
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    print(f"Loaded {len(rows)} records.")

    audit_results = []

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]

        print(
            f"Auditing records {start + 1} "
            f"to {start + len(batch)}..."
        )

        try:
            results = audit_batch(batch, start)

            if len(results) != len(batch):
                raise ValueError("Gemini returned an incorrect result count.")

            for result in results:
                suggested = result.get("suggested_label", "UNCERTAIN")
                quality = result.get("quality", "UNCERTAIN")

                if suggested not in INTENTS:
                    suggested = "UNCERTAIN"

                if quality not in {
                    "OK", "WRONG_LABEL", "UNCERTAIN", "TEXT_ERROR"
                }:
                    quality = "UNCERTAIN"

                record_id = int(result["id"])

                if not start <= record_id < start + len(batch):
                    raise ValueError("Invalid record ID returned.")

                original = rows[record_id]

                audit_results.append({
                    "id": record_id,
                    "text": original["text"],
                    "current_label": original["intent"],
                    "suggested_label": suggested,
                    "quality": quality,
                    "reason": result.get("reason", ""),
                })

        except Exception as error:
            print(f"Batch error: {error}")

            for i, row in enumerate(batch):
                audit_results.append({
                    "id": start + i,
                    "text": row["text"],
                    "current_label": row["intent"],
                    "suggested_label": "UNCERTAIN",
                    "quality": "UNCERTAIN",
                    "reason": "Audit batch failed; manual review required.",
                })

        time.sleep(1)

    audit_results.sort(key=lambda item: item["id"])

    with REPORT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "text",
                "current_label",
                "suggested_label",
                "quality",
                "reason",
            ],
        )
        writer.writeheader()
        writer.writerows(audit_results)

    print("\n========== AUDIT SUMMARY ==========")

    counts = {}

    for result in audit_results:
        quality = result["quality"]
        counts[quality] = counts.get(quality, 0) + 1

    for quality, count in sorted(counts.items()):
        print(f"{quality}: {count}")

    print(f"\nAudit report saved: {REPORT_PATH}")
    print("Original dataset was not modified.")


if __name__ == "__main__":
    main()

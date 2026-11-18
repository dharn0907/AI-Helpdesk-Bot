import csv
import json
import re
import time
import sys
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.llm_service import llm

DATA_DIR = BASE_DIR / "data"
DATASET_PATH = DATA_DIR / "business_intent_dataset.csv"

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "business_intent_dataset.csv"

TARGET_PER_INTENT = 100

INTENTS = [
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
]


def load_dataset():
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def generate_examples(intent, count):
    prompt = f"""
Generate exactly {count} realistic customer messages for a universal
business chatbot intent classifier.

Target intent: {intent}

Messages must:
- Be natural customer messages, not descriptions of the intent.
- Cover different industries: retail, SaaS, healthcare, travel,
  education, hospitality, finance, consulting and services.
- Include short, long, formal, informal and conversational wording.
- Use different sentence structures.
- Avoid duplicates and near-duplicates.
- Clearly express ONLY the target intent.
- Avoid answers, explanations and numbering.

Return ONLY valid JSON in this format:
{{"examples": ["message 1", "message 2"]}}
"""

    response = llm.invoke(prompt)
    content = response.content

    if isinstance(content, list):
        content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )

    content = str(content).strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    data = json.loads(content)
    examples = data.get("examples", [])

    return [
        text.strip()
        for text in examples
        if isinstance(text, str) and text.strip()
    ]


def main():
    rows = load_dataset()

    for intent in INTENTS:
        existing = {
            row["text"].strip().lower()
            for row in rows
            if row["intent"] == intent
        }

        needed = TARGET_PER_INTENT - len(existing)

        print(f"\n{intent}: need {needed} more examples")

        attempts = 0

        while needed > 0 and attempts < 5:
            attempts += 1
            batch_size = min(needed + 10, 50)

            try:
                generated = generate_examples(intent, batch_size)

                added = 0

                for example in generated:
                    key = example.lower()

                    if key not in existing:
                        rows.append({
                            "text": example,
                            "intent": intent
                        })
                        existing.add(key)
                        added += 1

                needed = TARGET_PER_INTENT - len(existing)

                print(
                    f"Attempt {attempts}: added {added}, "
                    f"remaining {needed}"
                )

            except Exception as error:
                print(f"Generation error: {error}")
                time.sleep(3)

        if needed > 0:
            print(f"WARNING: {intent} is short by {needed} examples")

    with DATASET_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["text", "intent"]
        )
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(row["intent"] for row in rows)

    print("\n========== FINAL DATASET ==========")
    print(f"Total examples: {len(rows)}")

    for intent in INTENTS:
        print(f"{intent}: {counts[intent]}")


if __name__ == "__main__":
    main()

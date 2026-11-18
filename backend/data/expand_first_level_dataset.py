
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

# Add the backend folder to Python's import path.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.llm_service import llm


DATASET_PATH = BASE_DIR / "data" / "first_level_dataset.csv"

TARGETS = {
    "BUSINESS_ENQUIRY": 60,
    "CUSTOMER_SUPPORT": 60,
    "GENERAL_QUERY": 60,
}

LABEL_GUIDANCE = {
    "BUSINESS_ENQUIRY": """
The user is exploring, evaluating, requesting, or intending to buy
a company's products or services. Include pricing, plans, quotations,
demos, bookings, subscriptions, consultations, partnerships,
appointments, and purchase enquiries.
""",
    "CUSTOMER_SUPPORT": """
The user needs assistance with an existing service, account, transaction,
complaint, technical problem, billing issue, refund, cancellation,
failed payment, or unresolved request. Include requests for human support.
""",
    "GENERAL_QUERY": """
The user is greeting, making casual conversation, asking general
non-transactional questions, seeking company information, asking about
website navigation, contact details, business hours, or platform identity.
""",
}

INDUSTRIES = [
    "software and SaaS",
    "healthcare services",
    "education and online learning",
    "banking and financial services",
    "insurance",
    "travel and hospitality",
    "real estate",
    "telecommunications",
    "retail",
    "logistics",
    "professional consulting",
    "fitness and wellness",
    "automotive services",
    "event management",
    "subscription services",
    "utilities",
    "recruitment",
    "cloud computing",
    "digital marketing",
    "property management",
]


def normalize_text(text):
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def extract_json(content):
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(getattr(item, "text", str(item)))
        content = "".join(parts)

    content = str(content).strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    start = content.find("[")
    end = content.rfind("]")

    if start == -1 or end == -1:
        raise ValueError("No JSON array found in Gemini response.")

    return json.loads(content[start:end + 1])


def generate_examples(intent, count, existing_texts):
    generated = []
    seen = set(existing_texts)

    # Maximum five attempts to collect the requested examples.
    for batch_number in range(1, 6):
        remaining = count - len(generated)

        if remaining <= 0:
            break

        batch_size = min(20, remaining)

        prompt = f"""
You are creating a high-quality training dataset for a universal
website chatbot intent classifier.

Generate exactly {batch_size} distinct customer messages.

TARGET INTENT: {intent}

INTENT DEFINITION:
{LABEL_GUIDANCE[intent]}

Use these industries for contextual variety:
{", ".join(INDUSTRIES)}

Requirements:
1. Write natural messages real customers might type.
2. Vary sentence structure, vocabulary, length, and tone.
3. Include short, long, direct, indirect, and conversational messages.
4. Do not invent company names or company facts.
5. Avoid repeated sentence patterns.
6. Avoid examples belonging to another intent.
7. Do not include explanations or answers.
8. Do not include numbered lists.
9. Every example must clearly represent the target intent.
10. Return valid JSON only.

Return this structure:
[
  {{"text": "customer message", "scenario": "short_scenario_name"}}
]
"""

        print(
            f"{intent}: requesting batch {batch_number}, "
            f"{batch_size} examples..."
        )

        response = llm.invoke(prompt)
        items = extract_json(response.content)

        accepted = 0

        for item in items:
            if not isinstance(item, dict):
                continue

            message = str(item.get("text", "")).strip()
            scenario = str(item.get("scenario", "generated")).strip()

            if not 3 <= len(message) <= 500:
                continue

            normalized = normalize_text(message)

            if normalized in seen:
                continue

            seen.add(normalized)

            generated.append({
                "text": message,
                "intent": intent,
                "scenario": scenario or "generated",
            })

            accepted += 1

            if len(generated) >= count:
                break

        print(
            f"{intent}: accepted {accepted}; "
            f"total collected {len(generated)}/{count}"
        )

        time.sleep(1)

    return generated


def main():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(DATASET_PATH)

    original = pd.read_csv(DATASET_PATH)

    required_columns = {"text", "intent", "scenario"}

    if not required_columns.issubset(original.columns):
        raise ValueError("Dataset is missing required columns.")

    original = original.dropna(
        subset=["text", "intent", "scenario"]
    ).copy()

    for column in ["text", "intent", "scenario"]:
        original[column] = original[column].astype(str).str.strip()

    original = original[
        original["text"].str.len().between(3, 500)
    ].copy()

    existing_labels = set(original["intent"].unique())

    if existing_labels != set(TARGETS):
        raise ValueError(
            f"Unexpected dataset labels: {existing_labels}"
        )

    original_counts = original["intent"].value_counts()

    if any(original_counts.get(label, 0) == 0 for label in TARGETS):
        raise ValueError("At least one category has no examples.")

    existing_texts = set(
        original["text"].map(normalize_text)
    )

    print("Existing examples:", len(original))
    print("Existing distribution:")
    print(original_counts.to_string())

    additions = []

    for intent, target in TARGETS.items():
        print(f"\nGenerating examples for {intent}...")

        examples = generate_examples(
            intent,
            target,
            existing_texts
        )

        additions.extend(examples)

    new_df = pd.DataFrame(
        additions,
        columns=["text", "intent", "scenario"]
    )

    combined = pd.concat(
        [original, new_df],
        ignore_index=True
    )

    combined["normalized_text"] = combined["text"].map(
        normalize_text
    )

    combined = combined.drop_duplicates(
        subset=["normalized_text"],
        keep="first"
    )

    combined = combined.drop(
        columns=["normalized_text"]
    )

    counts = combined["intent"].value_counts()

    print("\n========== DATASET QUALITY REPORT ==========")
    print("Original examples:", len(original))
    print("Generated examples:", len(new_df))
    print("Final unique examples:", len(combined))
    print("\nFinal class distribution:")
    print(counts.to_string())

    if set(counts.index) != set(TARGETS):
        raise ValueError("Unexpected intent categories detected.")

    # Require at least 100 examples per category before saving.
    if any(counts.get(label, 0) < 100 for label in TARGETS):
        raise ValueError(
            "Dataset expansion did not reach 100 examples "
            "in every category. Original dataset was not modified."
        )

    backup_path = DATASET_PATH.with_name(
        "first_level_dataset_backup.csv"
    )

    original.to_csv(backup_path, index=False)

    combined = combined.sample(
        frac=1,
        random_state=42
    ).reset_index(drop=True)

    combined.to_csv(DATASET_PATH, index=False)

    print("\nDataset expansion completed successfully.")
    print("Backup:", backup_path)
    print("Updated dataset:", DATASET_PATH)


if __name__ == "__main__":
    main()

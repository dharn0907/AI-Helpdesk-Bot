import pandas as pd
from pathlib import Path

data_dir = Path(__file__).resolve().parent
audit_path = data_dir / "business_intent_audit.csv"
output_path = data_dir / "business_intent_review.csv"

audit = pd.read_csv(audit_path)

review = audit[audit["quality"] == "WRONG_LABEL"].copy()

review = review.rename(columns={
    "current_label": "original_label",
    "suggested_label": "gemini_suggested_label"
})

review["final_label"] = ""
review["review_status"] = "PENDING"

review = review.sort_values(
    ["original_label", "gemini_suggested_label", "id"]
)

review.to_csv(output_path, index=False, encoding="utf-8-sig")

print("Review file created:", output_path)
print("Records to review:", len(review))
print("\nGrouped by label pair:")
print(
    review.groupby(
        ["original_label", "gemini_suggested_label"]
    ).size().sort_values(ascending=False).to_string()
)

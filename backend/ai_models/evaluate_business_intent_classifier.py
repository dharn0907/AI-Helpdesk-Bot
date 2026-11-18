from pathlib import Path

import pandas as pd
import torch

from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "data" / "business_intent_dataset_corrected.csv"
MODEL_PATH = BASE_DIR / "ai_models" / "business_intent_bert_model"
OUTPUT_PATH = BASE_DIR / "data" / "business_intent_test_errors.csv"

BATCH_SIZE = 8
MAX_LENGTH = 128
SEED = 42

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

df = pd.read_csv(DATASET_PATH)
df = df.dropna(subset=["text", "intent"]).copy()
df["text"] = df["text"].astype(str).str.strip()
df = df[df["text"] != ""]
df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)

labels = sorted(df["intent"].unique())
label_to_id = {label: i for i, label in enumerate(labels)}

df["label"] = df["intent"].map(label_to_id)

_, remaining_df = train_test_split(
    df,
    test_size=0.30,
    random_state=SEED,
    stratify=df["label"]
)

_, test_df = train_test_split(
    remaining_df,
    test_size=0.50,
    random_state=SEED,
    stratify=remaining_df["label"]
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()

encoded = tokenizer(
    test_df["text"].tolist(),
    padding="max_length",
    truncation=True,
    max_length=MAX_LENGTH,
    return_tensors="pt"
)

dataset = TensorDataset(
    encoded["input_ids"],
    encoded["attention_mask"]
)

loader = DataLoader(dataset, batch_size=BATCH_SIZE)

predictions = []

with torch.no_grad():
    for input_ids, attention_mask in loader:
        outputs = model(
            input_ids=input_ids.to(device),
            attention_mask=attention_mask.to(device)
        )
        predictions.extend(
            torch.argmax(outputs.logits, dim=1).cpu().tolist()
        )

test_df = test_df.copy()
test_df["predicted_intent"] = [
    labels[p] for p in predictions
]

errors = test_df[
    test_df["intent"] != test_df["predicted_intent"]
].copy()

errors = errors[["text", "intent", "predicted_intent"]]
errors.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

print("\n========== CONFUSION MATRIX ==========")
print(pd.DataFrame(
    confusion_matrix(
        test_df["intent"],
        test_df["predicted_intent"],
        labels=labels
    ),
    index=labels,
    columns=labels
).to_string())

print("\n========== MISCLASSIFIED EXAMPLES ==========")
print("Total errors:", len(errors))
print(errors.to_string(index=False))

print("\nError report saved at:", OUTPUT_PATH)

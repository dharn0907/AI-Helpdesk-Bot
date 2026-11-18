
from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR.parent / "ai_models" / "human_intervention_classifier"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 8
MAX_LENGTH = 128

print("Loading saved classifier...")
print("Device:", DEVICE)

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(DEVICE)
model.eval()

test_df = pd.read_csv(BASE_DIR / "test.csv")

class TestDataset(Dataset):
    def __init__(self, dataframe):
        self.texts = dataframe["text"].astype(str).tolist()
        self.labels = [
            model.config.label2id[label]
            for label in dataframe["label"]
        ]

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, index):
        encoding = tokenizer(
            self.texts[index],
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[index])
        }

dataset = TestDataset(test_df)
loader = DataLoader(dataset, batch_size=BATCH_SIZE)

actual = []
predicted = []

with torch.no_grad():
    for batch in loader:
        outputs = model(
            input_ids=batch["input_ids"].to(DEVICE),
            attention_mask=batch["attention_mask"].to(DEVICE)
        )

        predictions = torch.argmax(outputs.logits, dim=1)

        actual.extend(batch["labels"].tolist())
        predicted.extend(predictions.cpu().tolist())

label_names = [
    model.config.id2label[i]
    for i in range(model.config.num_labels)
]

print("\nTEST ACCURACY:")
print(accuracy_score(actual, predicted))

print("\nCLASSIFICATION REPORT:")
print(classification_report(
    actual,
    predicted,
    labels=list(range(len(label_names))),
    target_names=label_names,
    zero_division=0
))

print("\nCONFUSION MATRIX:")
print(confusion_matrix(
    actual,
    predicted,
    labels=list(range(len(label_names)))
))

print("\nTESTING COMPLETED!")

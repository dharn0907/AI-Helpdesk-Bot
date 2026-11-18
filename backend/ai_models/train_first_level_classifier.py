import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, f1_score


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "data" / "first_level_dataset.csv"
MODEL_PATH = Path(__file__).resolve().parent / "first_level_bert_model"

MODEL_NAME = "google-bert/bert-base-uncased"

MAX_LENGTH = 128
BATCH_SIZE = 8
EPOCHS = 5
LEARNING_RATE = 2e-5
SEED = 42
PATIENCE = 2

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Training device:", device)


# Load and validate dataset
df = pd.read_csv(DATASET_PATH)
df = df.dropna(subset=["text", "intent"]).copy()
df["text"] = df["text"].astype(str).str.strip()
df = df[df["text"] != ""]
df = df.drop_duplicates(subset=["text"])

EXPECTED_LABELS = {
    "BUSINESS_ENQUIRY",
    "CUSTOMER_SUPPORT",
    "GENERAL_QUERY"
}

labels = sorted(df["intent"].unique())

if set(labels) != EXPECTED_LABELS:
    raise ValueError(
        f"Expected exactly {EXPECTED_LABELS}, but found {set(labels)}"
    )

if df["intent"].value_counts().min() < 5:
    raise ValueError("Each class must contain at least 5 examples.")

label_to_id = {label: i for i, label in enumerate(labels)}
id_to_label = {i: label for label, i in label_to_id.items()}

df["label"] = df["intent"].map(label_to_id)

print("\nDataset examples:", len(df))
print("Class distribution:")
print(df["intent"].value_counts())


if len(df) < 300:
    print(
        "\nWARNING: This is a small pilot dataset. "
        "Do not treat its test score as production performance."
    )


# Stratified 70/15/15 split
train_texts, remaining_texts, train_labels, remaining_labels = (
    train_test_split(
        df["text"].tolist(),
        df["label"].tolist(),
        test_size=0.30,
        random_state=SEED,
        stratify=df["label"]
    )
)

val_texts, test_texts, val_labels, test_labels = train_test_split(
    remaining_texts,
    remaining_labels,
    test_size=0.50,
    random_state=SEED,
    stratify=remaining_labels
)

print("\nTraining examples:", len(train_texts))
print("Validation examples:", len(val_texts))
print("Testing examples:", len(test_texts))


# Load pretrained BERT
print("\nLoading pretrained BERT...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(labels),
    id2label=id_to_label,
    label2id=label_to_id
)

model.to(device)


def encode_texts(texts, targets):
    encoded = tokenizer(
        texts,
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt"
    )

    return TensorDataset(
        encoded["input_ids"],
        encoded["attention_mask"],
        torch.tensor(targets, dtype=torch.long)
    )


train_dataset = encode_texts(train_texts, train_labels)
val_dataset = encode_texts(val_texts, val_labels)
test_dataset = encode_texts(test_texts, test_labels)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE)


optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=0.01
)

best_val_f1 = -1.0
epochs_without_improvement = 0

MODEL_PATH.mkdir(parents=True, exist_ok=True)


# Training
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0.0

    for batch in train_loader:
        input_ids = batch[0].to(device)
        attention_mask = batch[1].to(device)
        labels_batch = batch[2].to(device)

        optimizer.zero_grad()

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels_batch
        )

        loss = outputs.loss
        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )

        optimizer.step()
        total_loss += loss.item()

    average_loss = total_loss / len(train_loader)

    # Validation
    model.eval()
    val_predictions = []
    val_actual = []

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch[0].to(device)
            attention_mask = batch[1].to(device)
            labels_batch = batch[2].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            val_predictions.extend(
                torch.argmax(outputs.logits, dim=1).cpu().tolist()
            )
            val_actual.extend(labels_batch.cpu().tolist())

    val_accuracy = accuracy_score(val_actual, val_predictions)
    val_f1 = f1_score(
        val_actual,
        val_predictions,
        average="macro",
        zero_division=0
    )

    print(
        f"\nEpoch {epoch + 1}/{EPOCHS} | "
        f"Loss: {average_loss:.4f} | "
        f"Validation Accuracy: {val_accuracy * 100:.2f}% | "
        f"Validation Macro F1: {val_f1:.4f}"
    )

    if val_f1 > best_val_f1:
        best_val_f1 = val_f1
        epochs_without_improvement = 0

        model.save_pretrained(MODEL_PATH)
        tokenizer.save_pretrained(MODEL_PATH)

        with open(MODEL_PATH / "labels.json", "w") as file:
            json.dump(label_to_id, file, indent=4)

        print("Best model saved.")
    else:
        epochs_without_improvement += 1

    if epochs_without_improvement >= PATIENCE:
        print("\nEarly stopping: validation score did not improve.")
        break


# Final testing using the best saved model
print("\nLoading best model for final testing...")

model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()

all_predictions = []
all_actual = []

with torch.no_grad():
    for batch in test_loader:
        input_ids = batch[0].to(device)
        attention_mask = batch[1].to(device)
        labels_batch = batch[2].to(device)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        predictions = torch.argmax(outputs.logits, dim=1)

        all_predictions.extend(predictions.cpu().tolist())
        all_actual.extend(labels_batch.cpu().tolist())

test_accuracy = accuracy_score(all_actual, all_predictions)
test_f1 = f1_score(
    all_actual,
    all_predictions,
    average="macro",
    zero_division=0
)

print("\n========== FINAL TEST RESULTS ==========")
print(f"Test Accuracy: {test_accuracy * 100:.2f}%")
print(f"Test Macro F1: {test_f1:.4f}")

print("\nClassification Report:")
print(
    classification_report(
        all_actual,
        all_predictions,
        labels=list(range(len(labels))),
        target_names=labels,
        zero_division=0
    )
)

print("\nFirst-level BERT training completed!")
print("Model saved at:", MODEL_PATH)

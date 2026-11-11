
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from torch.utils.data import DataLoader, TensorDataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "data" / "intent_dataset.csv"
MODEL_PATH = Path(__file__).resolve().parent / "bert_intent_model"

MODEL_NAME = "google-bert/bert-base-uncased"

MAX_LENGTH = 128
BATCH_SIZE = 8
EPOCHS = 3
LEARNING_RATE = 2e-5
SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Training device:", device)

# Load dataset
df = pd.read_csv(DATASET_PATH)
df = df.dropna(subset=["text", "intent"])
df["text"] = df["text"].astype(str)

labels = sorted(df["intent"].unique())

label_to_id = {label: i for i, label in enumerate(labels)}
id_to_label = {i: label for label, i in label_to_id.items()}

df["label"] = df["intent"].map(label_to_id)

print("Total examples:", len(df))
print("Intent categories:", labels)

# Split: 70% training, 15% validation, 15% testing
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

# Load BERT
print("\nLoading pretrained BERT...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(labels),
    id2label=id_to_label,
    label2id=label_to_id
)

model.to(device)


def encode_texts(texts, labels):
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
        torch.tensor(labels, dtype=torch.long)
    )


train_dataset = encode_texts(train_texts, train_labels)
val_dataset = encode_texts(val_texts, val_labels)
test_dataset = encode_texts(test_texts, test_labels)

train_loader = DataLoader(
    train_dataset, batch_size=BATCH_SIZE, shuffle=True
)

val_loader = DataLoader(
    val_dataset, batch_size=BATCH_SIZE
)

test_loader = DataLoader(
    test_dataset, batch_size=BATCH_SIZE
)

optimizer = torch.optim.AdamW(
    model.parameters(), lr=LEARNING_RATE
)

best_val_accuracy = 0.0

# Training and validation
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0

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
        optimizer.step()

        total_loss += loss.item()

    average_loss = total_loss / len(train_loader)

    # Validation
    model.eval()
    predictions = []
    actual = []

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch[0].to(device)
            attention_mask = batch[1].to(device)
            labels_batch = batch[2].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            predictions.extend(
                torch.argmax(outputs.logits, dim=1).cpu().tolist()
            )
            actual.extend(labels_batch.tolist())

    val_accuracy = accuracy_score(actual, predictions)

    print(
        f"Epoch {epoch + 1}/{EPOCHS} | "
        f"Loss: {average_loss:.4f} | "
        f"Validation Accuracy: {val_accuracy * 100:.2f}%"
    )

    if val_accuracy > best_val_accuracy:
        best_val_accuracy = val_accuracy

        MODEL_PATH.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(MODEL_PATH)
        tokenizer.save_pretrained(MODEL_PATH)

        with open(MODEL_PATH / "labels.json", "w") as file:
            json.dump(label_to_id, file, indent=4)

# Load best validation model
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
        all_actual.extend(labels_batch.tolist())

test_accuracy = accuracy_score(all_actual, all_predictions)

print("\nFINAL TEST RESULTS")
print("Best validation accuracy:", round(best_val_accuracy * 100, 2), "%")
print("Test accuracy:", round(test_accuracy * 100, 2), "%")

print("\nClassification Report:")

print(classification_report(
    all_actual,
    all_predictions,
    labels=list(range(len(labels))),
    target_names=labels,
    zero_division=0
))

print("\nBERT training completed!")
print("Model saved at:", MODEL_PATH)

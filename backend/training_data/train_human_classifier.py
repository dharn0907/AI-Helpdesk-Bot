
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup
)
from torch.optim import AdamW
from sklearn.metrics import accuracy_score, classification_report


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent

MODEL_NAME = "bert-base-uncased"
OUTPUT_DIR = BACKEND_DIR / "ai_models" / "human_intervention_classifier"

MAX_LENGTH = 128
BATCH_SIZE = 8
EPOCHS = 3
LEARNING_RATE = 2e-5

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

LABELS = [
    "AI_RESOLVABLE",
    "AI_ASSISTED_HUMAN_REQUIRED",
    "HUMAN_ONLY"
]

LABEL_TO_ID = {
    label: index for index, label in enumerate(LABELS)
}

ID_TO_LABEL = {
    index: label for label, index in LABEL_TO_ID.items()
}


# --------------------------------------------------
# 2. DISPLAY DEVICE
# --------------------------------------------------

print("=" * 55)
print("HUMAN INTERVENTION CLASSIFIER TRAINING")
print("=" * 55)

print("Device:", DEVICE)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))


# --------------------------------------------------
# 3. LOAD DATASETS
# --------------------------------------------------

train_df = pd.read_csv(BASE_DIR / "train.csv")
validation_df = pd.read_csv(BASE_DIR / "validation.csv")

for name, df in [
    ("Training", train_df),
    ("Validation", validation_df)
]:
    if df["text"].isna().any() or df["label"].isna().any():
        raise ValueError(f"{name} dataset contains missing values.")

    unknown_labels = set(df["label"]) - set(LABELS)

    if unknown_labels:
        raise ValueError(f"Unknown labels in {name}: {unknown_labels}")

print("\nTraining samples:", len(train_df))
print("Validation samples:", len(validation_df))


# --------------------------------------------------
# 4. LOAD TOKENIZER
# --------------------------------------------------

print("\nLoading BERT tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


# --------------------------------------------------
# 5. CREATE PYTORCH DATASET
# --------------------------------------------------

class ComplaintDataset(Dataset):

    def __init__(self, dataframe):
        self.texts = dataframe["text"].astype(str).tolist()
        self.labels = [
            LABEL_TO_ID[label]
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
            "labels": torch.tensor(
                self.labels[index],
                dtype=torch.long
            )
        }


train_dataset = ComplaintDataset(train_df)
validation_dataset = ComplaintDataset(validation_df)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

validation_loader = DataLoader(
    validation_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False
)


# --------------------------------------------------
# 6. LOAD BERT CLASSIFICATION MODEL
# --------------------------------------------------

print("\nLoading BERT classification model...")

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(LABELS),
    id2label=ID_TO_LABEL,
    label2id=LABEL_TO_ID
)

model.to(DEVICE)


# --------------------------------------------------
# 7. OPTIMIZER AND SCHEDULER
# --------------------------------------------------

optimizer = AdamW(
    model.parameters(),
    lr=LEARNING_RATE
)

total_steps = len(train_loader) * EPOCHS

scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=int(total_steps * 0.1),
    num_training_steps=total_steps
)


# --------------------------------------------------
# 8. VALIDATION FUNCTION
# --------------------------------------------------

def evaluate():

    model.eval()

    predictions = []
    actual_labels = []

    total_loss = 0

    with torch.no_grad():

        for batch in validation_loader:

            input_ids = batch["input_ids"].to(DEVICE)
            attention_mask = batch["attention_mask"].to(DEVICE)
            labels = batch["labels"].to(DEVICE)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )

            total_loss += outputs.loss.item()

            predicted = torch.argmax(
                outputs.logits,
                dim=1
            )

            predictions.extend(predicted.cpu().numpy())
            actual_labels.extend(labels.cpu().numpy())

    accuracy = accuracy_score(
        actual_labels,
        predictions
    )

    average_loss = total_loss / len(validation_loader)

    return average_loss, accuracy, actual_labels, predictions


# --------------------------------------------------
# 9. TRAINING LOOP
# --------------------------------------------------

best_accuracy = 0.0

print("\nStarting training...\n")

for epoch in range(EPOCHS):

    model.train()

    total_train_loss = 0

    for step, batch in enumerate(train_loader):

        input_ids = batch["input_ids"].to(DEVICE)
        attention_mask = batch["attention_mask"].to(DEVICE)
        labels = batch["labels"].to(DEVICE)

        optimizer.zero_grad(set_to_none=True)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )

        loss = outputs.loss

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )

        optimizer.step()
        scheduler.step()

        total_train_loss += loss.item()

        if (step + 1) % 50 == 0:
            print(
                f"Epoch {epoch + 1}/{EPOCHS} | "
                f"Batch {step + 1}/{len(train_loader)} | "
                f"Loss: {loss.item():.4f}"
            )

    average_train_loss = total_train_loss / len(train_loader)

    val_loss, val_accuracy, y_true, y_pred = evaluate()

    print("\n" + "-" * 55)
    print(f"Epoch: {epoch + 1}/{EPOCHS}")
    print(f"Training Loss: {average_train_loss:.4f}")
    print(f"Validation Loss: {val_loss:.4f}")
    print(f"Validation Accuracy: {val_accuracy:.4f}")
    print("-" * 55)

    if val_accuracy > best_accuracy:

        best_accuracy = val_accuracy

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        model.save_pretrained(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)

        with open(OUTPUT_DIR / "labels.json", "w") as file:
            json.dump(LABEL_TO_ID, file, indent=4)

        print("Best model saved!")


# --------------------------------------------------
# 10. FINAL VALIDATION REPORT
# --------------------------------------------------

print("\nFINAL VALIDATION REPORT")

print(
    classification_report(
        y_true,
        y_pred,
        labels=list(range(len(LABELS))),
        target_names=LABELS,
        zero_division=0
    )
)

print("Best validation accuracy:", round(best_accuracy, 4))
print("Model directory:", OUTPUT_DIR)

print("\nTRAINING COMPLETED!")

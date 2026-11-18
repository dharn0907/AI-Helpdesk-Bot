
"""Human intervention classification service using fine-tuned BERT."""

from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# Model location
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "ai_models" / "human_intervention_classifier"

# Select GPU when available
device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

# Load trained tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_PATH
)

model.to(device)
model.eval()


def classify_human_intervention(message: str):
    """
    Predict whether a complaint can be resolved by AI
    or requires human intervention.
    """

    if not message or not message.strip():
        raise ValueError("Complaint message cannot be empty.")

    # Tokenize customer complaint
    inputs = tokenizer(
        message,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    # Move input tensors to GPU or CPU
    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    # Run prediction
    with torch.no_grad():
        outputs = model(**inputs)

        probabilities = torch.softmax(
            outputs.logits,
            dim=1
        )

        confidence, predicted_id = torch.max(
            probabilities,
            dim=1
        )

    # Convert predicted ID into class label
    predicted_label = model.config.id2label[
        predicted_id.item()
    ]

    return {
        "message": message,
        "intervention": predicted_label,
        "confidence": round(confidence.item(), 4)
    }

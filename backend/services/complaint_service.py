
import json
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "ai_models" / "bert_intent_model"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load the trained model
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()

# Load intent labels
with open(MODEL_PATH / "labels.json", "r") as file:
    label_to_id = json.load(file)

id_to_label = {
    int(index): label
    for label, index in label_to_id.items()
}


def classify_complaint(message: str):

    if not message or not message.strip():
        raise ValueError("Complaint message cannot be empty.")

    # Convert customer message into BERT tokens
    inputs = tokenizer(
        message,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    # Predict complaint category
    with torch.no_grad():
        outputs = model(**inputs)

        probabilities = torch.softmax(outputs.logits, dim=1)

        confidence, predicted_id = torch.max(
            probabilities, dim=1
        )

    predicted_intent = id_to_label[predicted_id.item()]
    intent_confidence = round(confidence.item(), 4)

    # Safeguard: obvious account-login complaints must not be
    # mislabeled as cancellation or unrelated issue categories.
    normalized_message = " ".join(message.lower().split())
    login_cues = (
        "login", "log in", "logging in",
        "sign in", "signin", "sign-in",
        "forgot password", "reset password",
        "incorrect password", "wrong password",
        "unable to access account", "can't access account",
        "cannot access account", "account locked",
        "otp", "one time password",
    )

    if any(cue in normalized_message for cue in login_cues):
        predicted_intent = "login_issue"
        intent_confidence = 0.99

    return {
        "message": message,
        "intent": predicted_intent,
        "confidence": intent_confidence
    }

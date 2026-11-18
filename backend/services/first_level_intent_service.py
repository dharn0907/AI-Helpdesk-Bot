
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ai_models" / "first_level_bert_model"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MAX_LENGTH = 128

CONFIDENCE_THRESHOLD = 0.75
MARGIN_THRESHOLD = 0.15


class FirstLevelIntentClassifier:

    def __init__(self):
        if not MODEL_DIR.exists():
            raise FileNotFoundError(
                f"First-level model not found: {MODEL_DIR}"
            )

        self.tokenizer = AutoTokenizer.from_pretrained(
            str(MODEL_DIR)
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            str(MODEL_DIR)
        )

        self.model.to(DEVICE)
        self.model.eval()

        self.id2label = self.model.config.id2label

        print(
            f"First-level classifier loaded successfully on {DEVICE}"
        )

    def predict(self, message):

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message must be a non-empty string.")

        inputs = self.tokenizer(
            message.strip(),
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=MAX_LENGTH
        )

        inputs = {
            key: value.to(DEVICE)
            for key, value in inputs.items()
        }

        with torch.inference_mode():
            outputs = self.model(**inputs)
            probabilities = F.softmax(outputs.logits, dim=-1)[0]

        sorted_probabilities = torch.sort(
            probabilities,
            descending=True
        ).values

        predicted_id = int(torch.argmax(probabilities).item())
        predicted_intent = self.id2label[predicted_id]

        confidence = float(sorted_probabilities[0].item())
        second_confidence = float(sorted_probabilities[1].item())

        margin = confidence - second_confidence

        uncertain = (
            confidence < CONFIDENCE_THRESHOLD
            or margin < MARGIN_THRESHOLD
        )

        all_probabilities = {
            self.id2label[index]: round(float(probability.item()), 4)
            for index, probability in enumerate(probabilities)
        }

        return {
            "intent": predicted_intent,
            "confidence": round(confidence, 4),
            "second_confidence": round(second_confidence, 4),
            "margin": round(margin, 4),
            "uncertain": uncertain,
            "probabilities": all_probabilities
        }


first_level_classifier = FirstLevelIntentClassifier()


def classify_first_level_intent(message):
    return first_level_classifier.predict(message)

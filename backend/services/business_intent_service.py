from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ai_models" / "business_intent_bert_model"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MAX_LENGTH = 128


class BusinessIntentClassifier:

    def __init__(self):
        if not MODEL_DIR.exists():
            raise FileNotFoundError(f"Business model not found: {MODEL_DIR}")

        self.tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
        self.model = AutoModelForSequenceClassification.from_pretrained(
            str(MODEL_DIR)
        )

        self.model.to(DEVICE)
        self.model.eval()
        self.id2label = self.model.config.id2label

        print(f"Business Intent BERT loaded successfully on {DEVICE}")

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

        inputs = {key: value.to(DEVICE) for key, value in inputs.items()}

        with torch.inference_mode():
            outputs = self.model(**inputs)
            probabilities = F.softmax(outputs.logits, dim=-1)[0]

        predicted_id = int(torch.argmax(probabilities).item())

        return {
            "intent": self.id2label[predicted_id],
            "confidence": round(float(probabilities[predicted_id].item()), 4),
            "probabilities": {
                self.id2label[i]: round(float(p.item()), 4)
                for i, p in enumerate(probabilities)
            }
        }


business_intent_classifier = BusinessIntentClassifier()


def classify_business_intent(message):
    return business_intent_classifier.predict(message)

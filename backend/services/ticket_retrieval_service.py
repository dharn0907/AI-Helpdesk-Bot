
"""Historical knowledge base retrieval service."""

import json
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# Load the knowledge base
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_PATH = BASE_DIR / "data" / "knowledge_base.json"

with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as file:
    knowledge_base = json.load(file)


# Load the sentence embedding model
print("Loading sentence transformer model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Sentence transformer model loaded successfully!")


# Prepare complaint embeddings
complaints = [
    item["problem"] for item in knowledge_base
]

complaint_embeddings = model.encode(
    complaints,
    convert_to_numpy=True
)


def retrieve_solution(user_message: str, intent: str):
    """Find the most similar solved complaint."""

    if not user_message.strip():
        return None

    # Convert the new complaint into an embedding
    user_embedding = model.encode(
        [user_message],
        convert_to_numpy=True
    )

    # Calculate semantic similarity
    similarities = cosine_similarity(
        user_embedding,
        complaint_embeddings
    )[0]

    # Only consider tickets with matching intent and solved status
    eligible_indices = [
        i for i, item in enumerate(knowledge_base)
        if item.get("intent") == intent
        and item.get("status") in ("solved", "closed")
    ]

    if not eligible_indices:
        return None

    # Find the best matching eligible complaint
    best_index = max(
        eligible_indices,
        key=lambda i: similarities[i]
    )

    best_score = float(similarities[best_index])

    # Initial experimental threshold
    if best_score < 0.50:
        return None

    matched_ticket = knowledge_base[best_index]

    return {
        "ticket_id": matched_ticket["id"],
        "problem": matched_ticket["problem"],
        "solution": matched_ticket["solution"],
        "similarity": round(best_score, 4)
    }

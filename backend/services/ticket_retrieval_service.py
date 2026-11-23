
"""Historical and agent-approved ticket resolution retrieval."""

import json
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from database.database import SessionLocal
from database.models import TicketResolutionReview


# ------------------------------------------------
# LEGACY JSON KNOWLEDGE BASE
# ------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_PATH = BASE_DIR / "data" / "knowledge_base.json"

with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as file:
    knowledge_base = json.load(file)


# ------------------------------------------------
# SHARED SEMANTIC EMBEDDING MODEL
# ------------------------------------------------

print("Loading sentence transformer model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Sentence transformer model loaded successfully!")


complaints = [item["problem"] for item in knowledge_base]

complaint_embeddings = model.encode(
    complaints,
    convert_to_numpy=True
)


# ------------------------------------------------
# AGENT-APPROVED DATABASE RETRIEVAL
# ------------------------------------------------

def retrieve_approved_solution(
    user_message: str,
    intent: str,
    company_id: int,
    chatbot_id: int,
    threshold: float = 0.40,
):
    """
    Retrieve the most similar agent-approved resolution
    belonging to the same company and chatbot.

    Rejected and unreviewed resolutions are excluded.
    """

    if not user_message or not user_message.strip():
        return None

    if company_id is None or chatbot_id is None:
        print("APPROVED RETRIEVAL: Missing company_id or chatbot_id")
        return None

    db = SessionLocal()

    try:
        approved_records = (
            db.query(TicketResolutionReview)
            .filter(
                TicketResolutionReview.company_id == company_id,
                TicketResolutionReview.chatbot_id == chatbot_id,
                TicketResolutionReview.approval_status == "approved",
                TicketResolutionReview.intent == intent,
                TicketResolutionReview.approved_solution.isnot(None),
                TicketResolutionReview.approved_solution != "",
            )
            .all()
        )

        print("\n===== APPROVED RESOLUTION DEBUG =====")
        print("USER COMPLAINT:", user_message)
        print("USER INTENT:", intent)
        print("COMPANY ID:", company_id)
        print("CHATBOT ID:", chatbot_id)
        print("APPROVED RECORD COUNT:", len(approved_records))

        if not approved_records:
            print("RESULT: No approved records for this company/chatbot/intent")
            print("===== DEBUG END =====\n")
            return None

        approved_complaints = [
            record.complaint for record in approved_records
        ]

        user_embedding = model.encode(
            [user_message],
            convert_to_numpy=True
        )

        approved_embeddings = model.encode(
            approved_complaints,
            convert_to_numpy=True
        )

        similarities = cosine_similarity(
            user_embedding,
            approved_embeddings
        )[0]

        best_index = int(similarities.argmax())
        best_score = float(similarities[best_index])

        matched_record = approved_records[best_index]

        print("BEST MATCH TICKET:", matched_record.ticket_id)
        print("MATCHED COMPLAINT:", matched_record.complaint)
        print("SIMILARITY SCORE:", round(best_score, 4))
        print("THRESHOLD:", threshold)

        if best_score < threshold:
            print("RESULT: Rejected because similarity is below threshold")
            print("===== DEBUG END =====\n")
            return None

        print("RESULT: APPROVED MATCH FOUND")
        print("===== DEBUG END =====\n")

        return {
            "ticket_id": matched_record.ticket_id,
            "problem": matched_record.complaint,
            "solution": matched_record.approved_solution,
            "intent": matched_record.intent,
            "company_id": matched_record.company_id,
            "chatbot_id": matched_record.chatbot_id,
            "similarity": round(best_score, 4),
            "source": "agent_approved_resolution",
        }

    finally:
        db.close()


# ------------------------------------------------
# LEGACY JSON RETRIEVAL
# ------------------------------------------------

def retrieve_solution(user_message: str, intent: str):
    """Find the most similar solved complaint in the legacy JSON KB."""

    if not user_message or not user_message.strip():
        return None

    user_embedding = model.encode(
        [user_message],
        convert_to_numpy=True
    )

    similarities = cosine_similarity(
        user_embedding,
        complaint_embeddings
    )[0]

    eligible_indices = [
        i for i, item in enumerate(knowledge_base)
        if item.get("intent") == intent
        and item.get("status") in ("solved", "closed")
    ]

    if not eligible_indices:
        return None

    best_index = max(
        eligible_indices,
        key=lambda i: similarities[i]
    )

    best_score = float(similarities[best_index])

    if best_score < 0.50:
        return None

    matched_ticket = knowledge_base[best_index]

    return {
        "ticket_id": matched_ticket["id"],
        "problem": matched_ticket["problem"],
        "solution": matched_ticket["solution"],
        "similarity": round(best_score, 4),
        "source": "legacy_json_knowledge_base",
    }

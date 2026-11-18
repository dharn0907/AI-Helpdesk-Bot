
"""Semantic duplicate detection for unresolved support tickets."""

from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import func

from database.models import Ticket
from services.ticket_retrieval_service import model

SIMILARITY_THRESHOLD = 0.70


def detect_duplicate_ticket(
    db,
    customer_message,
    intent,
    additional_details=None,
    customer_email=None
):
    """
    Find a potential duplicate among unresolved tickets
    belonging to the same customer email.

    This function never creates, closes, or blocks tickets.
    """

    if not customer_message or not customer_message.strip():
        return None

    if not customer_email or not customer_email.strip():
        return None

    unresolved_tickets = (
        db.query(Ticket)
        .filter(
            func.lower(Ticket.status).in_(["open", "in progress"]),
            Ticket.intent == intent,
            func.lower(Ticket.customer_email) == customer_email.strip().lower()
        )
        .all()
    )

    if not unresolved_tickets:
        return None

    new_complaint = customer_message.strip()

    if additional_details and additional_details.strip():
        new_complaint += " " + additional_details.strip()

    existing_complaints = []

    for ticket in unresolved_tickets:
        complaint = ticket.customer_message or ""

        if ticket.additional_details:
            complaint += " " + ticket.additional_details

        existing_complaints.append(complaint)

    new_embedding = model.encode(
        [new_complaint],
        convert_to_numpy=True
    )

    existing_embeddings = model.encode(
        existing_complaints,
        convert_to_numpy=True
    )

    similarities = cosine_similarity(
        new_embedding,
        existing_embeddings
    )[0]

    best_index = int(similarities.argmax())
    best_score = float(similarities[best_index])

    if best_score < SIMILARITY_THRESHOLD:
        return None

    matched_ticket = unresolved_tickets[best_index]

    return {
        "duplicate_found": True,
        "ticket_id": matched_ticket.ticket_id,
        "status": matched_ticket.status,
        "customer_message": matched_ticket.customer_message,
        "similarity": round(best_score, 4)
    }

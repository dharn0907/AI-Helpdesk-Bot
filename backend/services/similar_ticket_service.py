"""Semantic detection of similar unresolved support tickets."""

from sklearn.metrics.pairwise import cosine_similarity

from database.models import Ticket
from services.ticket_retrieval_service import model


SIMILARITY_THRESHOLD = 0.60

def _ticket_text(ticket):
    """Combine complaint and additional details for comparison."""

    text = ticket.customer_message or ""

    if ticket.additional_details:
        text += " " + ticket.additional_details

    return text.strip()


def find_similar_tickets(
    db,
    ticket_id,
    threshold=SIMILARITY_THRESHOLD,
    max_results=10,
):
    """
    Find semantically similar unresolved tickets from the same company.

    Only tickets with the same intent are compared.

    This function does not merge, modify, close, or reply to tickets.
    """

    target_ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id)
        .first()
    )

    if not target_ticket:
        return None

    if not target_ticket.company_id:
        return {
            "ticket_id": target_ticket.ticket_id,
            "similar_tickets": [],
            "message": "Ticket has no company association.",
        }

    target_text = _ticket_text(target_ticket)

    if not target_text:
        return {
            "ticket_id": target_ticket.ticket_id,
            "similar_tickets": [],
        }

    unresolved_statuses = [
        "open",
        "in progress",
        "pending",
    ]

    candidates = (
        db.query(Ticket)
        .filter(
            Ticket.company_id == target_ticket.company_id,
            Ticket.ticket_id != target_ticket.ticket_id,
            Ticket.intent == target_ticket.intent,
            Ticket.status.ilike("open")
            | Ticket.status.ilike("in progress")
            | Ticket.status.ilike("pending"),
        )
        .order_by(Ticket.created_at.desc())
        .limit(500)
        .all()
    )

    if not candidates:
        return {
            "ticket_id": target_ticket.ticket_id,
            "similar_tickets": [],
        }

    candidate_texts = [
        _ticket_text(ticket)
        for ticket in candidates
    ]

    valid_indices = [
        i for i, text in enumerate(candidate_texts)
        if text
    ]

    if not valid_indices:
        return {
            "ticket_id": target_ticket.ticket_id,
            "similar_tickets": [],
        }

    valid_candidates = [
        candidates[i] for i in valid_indices
    ]

    valid_texts = [
        candidate_texts[i] for i in valid_indices
    ]

    embeddings = model.encode(
        [target_text] + valid_texts,
        convert_to_numpy=True,
    )

    similarities = cosine_similarity(
        embeddings[0:1],
        embeddings[1:],
    )[0]

    matches = []

    for index, score in enumerate(similarities):

        score = float(score)

        if score < threshold:
            continue

        ticket = valid_candidates[index]

        matches.append({
            "ticket_id": ticket.ticket_id,
            "customer_message": ticket.customer_message,
            "additional_details": ticket.additional_details,
            "agent_reply": ticket.agent_reply,
            "customer_email": ticket.customer_email,
            "intent": ticket.intent,
            "category": ticket.category,
            "status": ticket.status,
            "priority": ticket.priority,
            "similarity": round(score, 4),
            "similarity_percent": round(score * 100, 2),
            "created_at": ticket.created_at,
        })

    matches.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    matches = matches[:max_results]

    return {
        "ticket_id": target_ticket.ticket_id,
        "company_id": target_ticket.company_id,
        "intent": target_ticket.intent,
        "similar_tickets": matches,
        "total_matches": len(matches),
        "threshold": threshold,
    }
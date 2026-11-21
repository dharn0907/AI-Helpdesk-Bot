
"""Ticket management APIs for human support agents."""

import uuid
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from services.similar_ticket_service import find_similar_tickets

from database.database import Base, engine, get_db
from database.models import Company, Ticket, TicketResolutionReview
from services.email_service import send_ticket_reply
from services.llm_service import llm
router = APIRouter(prefix="/tickets", tags=["Ticket Management"])

Base.metadata.create_all(bind=engine)


@router.post("/")
def create_ticket(data: dict, db: Session = Depends(get_db)):

    customer_message = data.get("customer_message", "").strip()
    intent = data.get("intent", "general_enquiry")
    session_id = data.get("session_id")
    additional_details = data.get("additional_details", "")
    customer_email = data.get("customer_email")

    if not customer_message:
        raise HTTPException(
            status_code=400,
            detail="Customer complaint cannot be empty."
        )

    ticket = Ticket(
        ticket_id=f"TKT-{uuid.uuid4().hex[:8].upper()}",
        session_id=session_id,
        company_id=1,
        customer_message=customer_message,
        additional_details=additional_details,
        customer_email=customer_email,
        intent=intent,
        priority="Medium",
        status="Open"
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {
        "message": "Ticket created successfully.",
        "ticket_id": ticket.ticket_id,
        "status": ticket.status
    }


@router.get("/")
def get_all_tickets(db: Session = Depends(get_db)):

    tickets = db.query(Ticket).order_by(
        Ticket.created_at.desc()
    ).all()

    return tickets


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):

    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    return ticket


@router.patch("/{ticket_id}")
def update_ticket(
    ticket_id: str,
    data: dict,
    db: Session = Depends(get_db)
):

    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    if "status" in data:
        allowed_statuses = [
            "Open",
            "In Progress",
            "Resolved",
            "Closed"
        ]

        if data["status"] not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid ticket status."
            )

        ticket.status = data["status"]

    email_sent = None
    email_message = "No email was sent."

    if "agent_reply" in data:

        agent_reply = str(data["agent_reply"]).strip()

        if not agent_reply:
            raise HTTPException(
                status_code=400,
                detail="Agent reply cannot be empty."
            )

        # Save the reply first, even if email delivery later fails.
        ticket.agent_reply = agent_reply

        db.commit()
        db.refresh(ticket)

        email_sent, email_message = send_ticket_reply(
            customer_email=ticket.customer_email,
            ticket_id=ticket.ticket_id,
            customer_message=ticket.customer_message,
            agent_reply=agent_reply
        )

    else:
        db.commit()
        db.refresh(ticket)

    return {
        "message": "Ticket updated successfully.",
        "ticket_id": ticket.ticket_id,
        "status": ticket.status,
        "agent_reply": ticket.agent_reply,
        "email_sent": email_sent,
        "email_message": email_message
    }



@router.post("/{ticket_id}/resolution-review")
def review_ticket_resolution(
    ticket_id: str,
    data: dict,
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    if ticket.status not in ["Resolved", "Closed"]:
        raise HTTPException(
            status_code=400,
            detail="Only resolved or closed tickets can be reviewed."
        )

    if not ticket.agent_reply or not ticket.agent_reply.strip():
        raise HTTPException(
            status_code=400,
            detail="The ticket must have an agent reply before review."
        )

    decision = str(data.get("decision", "")).strip().lower()

    if decision not in ["yes", "no"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be yes or no."
        )

    reusable_solution = str(
        data.get("approved_solution", "")
    ).strip()

    if decision == "yes" and not reusable_solution:
        raise HTTPException(
            status_code=400,
            detail="Please provide a reusable solution before approving."
        )

    company = db.query(Company).filter(
        Company.is_active.is_(True)
    ).order_by(Company.id.asc()).first()

    if not company:
        raise HTTPException(
            status_code=400,
            detail="No active company is available."
        )

    review = db.query(TicketResolutionReview).filter(
        TicketResolutionReview.ticket_id == ticket.ticket_id
    ).first()

    if not review:
        review = TicketResolutionReview(
            ticket_id=ticket.ticket_id,
            company_id=company.id,
            complaint=ticket.customer_message,
            intent=ticket.intent
        )
        db.add(review)

    review.company_id = company.id
    review.complaint = ticket.customer_message
    review.intent = ticket.intent
    review.approval_status = (
        "approved" if decision == "yes" else "rejected"
    )
    review.approved_solution = (
        reusable_solution if decision == "yes" else ""
    )
    review.approved_at = (
        datetime.now(timezone.utc) if decision == "yes" else None
    )

    db.commit()
    db.refresh(review)

    return {
        "message": (
            "Solution approved for chatbot use."
            if decision == "yes"
            else "Solution rejected and excluded from chatbot knowledge."
        ),
        "ticket_id": ticket.ticket_id,
        "approval_status": review.approval_status,
        "approved_solution": review.approved_solution
    }



@router.get("/{ticket_id}/resolution-review")
def get_ticket_resolution_review(
    ticket_id: str,
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    review = db.query(TicketResolutionReview).filter(
        TicketResolutionReview.ticket_id == ticket.ticket_id
    ).first()

    if not review:
        return {
            "ticket_id": ticket.ticket_id,
            "approval_status": None,
            "approved_solution": ""
        }

    return {
        "ticket_id": ticket.ticket_id,
        "approval_status": review.approval_status,
        "approved_solution": review.approved_solution
    }
@router.post("/{ticket_id}/summarize")
def summarize_ticket(
    ticket_id: str,
    data: dict,
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    mode = str(data.get("mode", "")).strip().lower()

    if mode not in ["normal", "fields"]:
        raise HTTPException(
            status_code=400,
            detail="Mode must be normal or fields."
        )

    ticket_context = f"""
Customer complaint:
{ticket.customer_message or ""}

Additional customer information:
{ticket.additional_details or ""}

Customer email:
{ticket.customer_email or ""}

Ticket category:
{ticket.intent or ""}

Agent response:
{ticket.agent_reply or ""}
"""

    if mode == "normal":

        prompt = f"""
You are an AI assistant helping a human support agent
understand customer support tickets.

Summarize the following ticket into one concise paragraph.

Rules:
- Clearly explain the customer's main problem.
- Include relevant details.
- Include troubleshooting already attempted if available.
- Include the customer's expected outcome if available.
- Do not invent information.
- Do not repeat irrelevant information.
- Do not use headings or bullet points.
- Return only the summary paragraph.

TICKET:
{ticket_context}
"""

    else:

        prompt = f"""
You are an AI assistant helping a human support agent
understand customer support tickets.

Extract the relevant information into structured fields.

Possible fields:
- Issue
- Product or Service
- Error Message
- Steps Already Tried
- Expected Outcome
- Actual Outcome
- Customer Requirements
- Relevant Technical Details
- Impact

Rules:
- Extract only information explicitly available in the ticket.
- Never invent or assume information.
- Include only fields that contain actual information.
- Omit missing fields completely.
- Never write "Not provided", "Unknown", or "N/A".
- Keep field values concise and informative.
- Return valid JSON only.
- Return a JSON object, not an array.
- Do not include Markdown code fences.

TICKET:
{ticket_context}

Return the JSON object.
"""

    try:
        response = llm.invoke(prompt)

        content = response.content

        if isinstance(content, list):
            content = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            )

        content = str(content).strip()

        if mode == "normal":
            return {
                "ticket_id": ticket.ticket_id,
                "mode": "normal",
                "summary": content
            }

        # Remove Markdown code fences if returned by the LLM
        if content.startswith("```"):
            content = content.replace("```json", "")
            content = content.replace("```", "")
            content = content.strip()

        extracted_fields = json.loads(content)

        if not isinstance(extracted_fields, dict):
            raise ValueError(
                "AI response must be a JSON object."
            )

        # Remove empty or placeholder values
        extracted_fields = {
            key: value
            for key, value in extracted_fields.items()
            if value is not None
            and str(value).strip()
            and str(value).strip().lower() not in [
                "not provided",
                "unknown",
                "n/a",
                "none",
                "null"
            ]
        }

        return {
            "ticket_id": ticket.ticket_id,
            "mode": "fields",
            "fields": extracted_fields
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ticket summarization failed: {str(exc)}"
        )
@router.get("/{ticket_id}/similar")
def get_similar_tickets(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    """Find similar tickets for the selected ticket."""

    result = find_similar_tickets(
        db=db,
        ticket_id=ticket_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found.",
        )

    return result
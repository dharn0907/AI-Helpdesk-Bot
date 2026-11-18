
"""Ticket management APIs for human support agents."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import Base, engine, get_db
from database.models import Ticket
from services.email_service import send_ticket_reply

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

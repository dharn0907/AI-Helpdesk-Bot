
"""MCP server for the AI Helpdesk Bot."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mcp.server import MCPServer
from sqlalchemy import desc

from database.database import SessionLocal
from database.models import Ticket
from services.ticket_retrieval_service import retrieve_solution


server = MCPServer(
    name="AI Helpdesk MCP Server",
    version="1.0.0",
    instructions=(
        "Provides tools for historical ticket retrieval, "
        "Supabase ticket access, and helpdesk operations."
    ),
)


@server.tool(
    name="test_helpdesk_connection",
    description="Test whether the AI Helpdesk MCP server is working.",
)
def test_helpdesk_connection() -> str:
    return (
        "MCP connection successful! "
        "AI Helpdesk MCP Server is running correctly."
    )


@server.tool(
    name="search_solved_tickets",
    description=(
        "Search historical solved or closed complaints "
        "using semantic similarity and complaint intent."
    ),
)
def search_solved_tickets(user_message: str, intent: str) -> dict:

    if not user_message or not user_message.strip():
        return {"found": False, "message": "Customer complaint cannot be empty."}

    if not intent or not intent.strip():
        return {"found": False, "message": "Complaint intent cannot be empty."}

    result = retrieve_solution(
        user_message=user_message.strip(),
        intent=intent.strip()
    )

    if result is None:
        return {
            "found": False,
            "message": "No sufficiently similar solved or closed ticket was found."
        }

    return {
        "found": True,
        "ticket_id": result["ticket_id"],
        "problem": result["problem"],
        "solution": result["solution"],
        "similarity": result["similarity"]
    }


@server.tool(
    name="get_ticket_details",
    description=(
        "Retrieve an existing helpdesk ticket from Supabase "
        "using its ticket ID. This is a read-only operation."
    ),
)
def get_ticket_details(ticket_id: str) -> dict:

    if not ticket_id or not ticket_id.strip():
        return {"found": False, "message": "Ticket ID cannot be empty."}

    db = SessionLocal()

    try:
        ticket = (
            db.query(Ticket)
            .filter(Ticket.ticket_id == ticket_id.strip())
            .first()
        )

        if ticket is None:
            return {
                "found": False,
                "message": f"No ticket found with ID {ticket_id}."
            }

        return {
            "found": True,
            "ticket": {
                "id": ticket.id,
                "ticket_id": ticket.ticket_id,
                "session_id": ticket.session_id,
                "customer_message": ticket.customer_message,
                "additional_details": ticket.additional_details,
                "customer_email": ticket.customer_email,
                "intent": ticket.intent,
                "priority": ticket.priority,
                "status": ticket.status,
                "agent_reply": ticket.agent_reply,
                "created_at": (
                    ticket.created_at.isoformat()
                    if ticket.created_at else None
                ),
                "updated_at": (
                    ticket.updated_at.isoformat()
                    if ticket.updated_at else None
                )
            }
        }

    except Exception as error:
        return {
            "found": False,
            "message": "Unable to retrieve ticket details.",
            "error": str(error)
        }

    finally:
        db.close()


@server.tool(
    name="get_customer_ticket_history",
    description=(
        "Retrieve the recent helpdesk ticket history for a customer "
        "using their email address. Returns ticket IDs, complaints, "
        "intents, priorities, statuses, and timestamps."
    ),
)
def get_customer_ticket_history(customer_email: str) -> dict:

    if not customer_email or not customer_email.strip():
        return {
            "found": False,
            "message": "Customer email cannot be empty."
        }

    db = SessionLocal()

    try:
        tickets = (
            db.query(Ticket)
            .filter(Ticket.customer_email == customer_email.strip())
            .order_by(desc(Ticket.created_at))
            .limit(20)
            .all()
        )

        if not tickets:
            return {
                "found": False,
                "message": "No ticket history found for this customer.",
                "total_tickets": 0,
                "tickets": []
            }

        history = []

        for ticket in tickets:
            history.append({
                "ticket_id": ticket.ticket_id,
                "customer_message": ticket.customer_message,
                "intent": ticket.intent,
                "priority": ticket.priority,
                "status": ticket.status,
                "agent_reply": ticket.agent_reply,
                "created_at": (
                    ticket.created_at.isoformat()
                    if ticket.created_at else None
                )
            })

        return {
            "found": True,
            "customer_email": customer_email.strip(),
            "total_tickets": len(history),
            "tickets": history
        }

    except Exception as error:
        return {
            "found": False,
            "message": "Unable to retrieve customer ticket history.",
            "error": str(error)
        }

    finally:
        db.close()


if __name__ == "__main__":
    print("Starting AI Helpdesk MCP Server...")

    server.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
    )

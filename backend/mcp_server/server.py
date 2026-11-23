"""MCP server for the AI Helpdesk Bot."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mcp.server.fastmcp import FastMCP
from sqlalchemy import desc

from database.database import SessionLocal
from database.models import Ticket
from services.ticket_retrieval_service import retrieve_approved_solution


server = FastMCP(
    name="AI Helpdesk MCP Server",
    instructions=(
        "Provides chatbot-scoped historical ticket retrieval, "
        "ticket access, and helpdesk operations. "
        "All data retrieval must be scoped to the requesting "
        "company and chatbot."
    ),
    host="127.0.0.1",
    port=8001,
)


def validate_scope(company_id: int, chatbot_id: int) -> bool:
    return (
        isinstance(company_id, int)
        and isinstance(chatbot_id, int)
        and company_id > 0
        and chatbot_id > 0
    )


@server.tool(
    name="test_helpdesk_connection",
    description="Test whether the AI Helpdesk MCP server is working.",
)
def test_helpdesk_connection() -> str:
    return "MCP connection successful! AI Helpdesk MCP Server is running correctly."


@server.tool(
    name="search_solved_tickets",
    description=(
        "Search approved historical solutions using semantic similarity "
        "and complaint intent. Requires company_id and chatbot_id "
        "to prevent cross-chatbot knowledge access."
    ),
)
def search_solved_tickets(
    user_message: str,
    intent: str,
    company_id: int,
    chatbot_id: int,
) -> dict:

    if not validate_scope(company_id, chatbot_id):
        return {
            "found": False,
            "message": "Invalid company or chatbot scope.",
        }

    if not user_message or not user_message.strip():
        return {
            "found": False,
            "message": "Customer complaint cannot be empty.",
        }

    if not intent or not intent.strip():
        return {
            "found": False,
            "message": "Complaint intent cannot be empty.",
        }

    try:
        result = retrieve_approved_solution(
            user_message=user_message.strip(),
            intent=intent.strip(),
            company_id=company_id,
            chatbot_id=chatbot_id,
        )

        if result is None:
            return {
                "found": False,
                "message": (
                    "No sufficiently similar approved solution "
                    "was found for this chatbot."
                ),
            }

        return {
            "found": True,
            "ticket_id": result.get("ticket_id"),
            "problem": result.get("problem"),
            "solution": result.get("solution"),
            "similarity": result.get("similarity"),
            "company_id": company_id,
            "chatbot_id": chatbot_id,
        }

    except Exception as exc:
        print(f"MCP retrieval error: {exc}")
        import traceback
        traceback.print_exc()

        return {
            "found": False,
            "message": "Unable to search approved solutions.",
        }


@server.tool(
    name="get_ticket_details",
    description=(
        "Retrieve an existing helpdesk ticket using its ticket ID. "
        "Results are restricted to the specified company and chatbot."
    ),
)
def get_ticket_details(
    ticket_id: str,
    company_id: int,
    chatbot_id: int,
) -> dict:

    if not validate_scope(company_id, chatbot_id):
        return {
            "found": False,
            "message": "Invalid company or chatbot scope.",
        }

    if not ticket_id or not ticket_id.strip():
        return {
            "found": False,
            "message": "Ticket ID cannot be empty.",
        }

    db = SessionLocal()

    try:
        ticket = (
            db.query(Ticket)
            .filter(
                Ticket.ticket_id == ticket_id.strip(),
                Ticket.company_id == company_id,
                Ticket.chatbot_id == chatbot_id,
            )
            .first()
        )

        if ticket is None:
            return {
                "found": False,
                "message": "Ticket not found for this chatbot.",
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
                ),
            },
        }

    except Exception:
        return {
            "found": False,
            "message": "Unable to retrieve ticket details.",
        }

    finally:
        db.close()


@server.tool(
    name="get_customer_ticket_history",
    description=(
        "Retrieve recent ticket history for a customer email. "
        "History is restricted to the specified company and chatbot."
    ),
)
def get_customer_ticket_history(
    customer_email: str,
    company_id: int,
    chatbot_id: int,
) -> dict:

    if not validate_scope(company_id, chatbot_id):
        return {
            "found": False,
            "message": "Invalid company or chatbot scope.",
        }

    if not customer_email or not customer_email.strip():
        return {
            "found": False,
            "message": "Customer email cannot be empty.",
        }

    db = SessionLocal()

    try:
        tickets = (
            db.query(Ticket)
            .filter(
                Ticket.customer_email == customer_email.strip(),
                Ticket.company_id == company_id,
                Ticket.chatbot_id == chatbot_id,
            )
            .order_by(desc(Ticket.created_at))
            .limit(20)
            .all()
        )

        if not tickets:
            return {
                "found": False,
                "message": "No ticket history found for this chatbot.",
                "total_tickets": 0,
                "tickets": [],
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
                ),
            })

        return {
            "found": True,
            "customer_email": customer_email.strip(),
            "total_tickets": len(history),
            "tickets": history,
        }

    except Exception:
        return {
            "found": False,
            "message": "Unable to retrieve customer ticket history.",
        }

    finally:
        db.close()


if __name__ == "__main__":
    print("Starting AI Helpdesk MCP Server on http://127.0.0.1:8001")

    server.run(transport="streamable-http")
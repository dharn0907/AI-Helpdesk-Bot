
"""Application entry point for the helpdesk backend."""

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from routes.image import router as image_router
from routes.ticket_routes import router as ticket_router

from services.ticket_retrieval_service import retrieve_solution
from services.complaint_service import classify_complaint
from services.response_service import generate_support_response

from database.database import SessionLocal
from database.models import Ticket


app = FastAPI(title="AI Helpdesk Bot")

# Temporary conversation state for the prototype
conversation_states = {}


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "AI Helpdesk Backend is running!"}


def create_support_ticket(customer_message, intent, session_id):
    """Save an unresolved customer complaint as a database ticket."""

    db = SessionLocal()

    try:
        ticket = Ticket(
            ticket_id=f"TKT-{uuid.uuid4().hex[:8].upper()}",
            session_id=session_id,
            customer_message=customer_message,
            intent=intent,
            priority="Medium",
            status="Open"
        )

        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        return ticket.ticket_id

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.post("/chat")
def chat(data: dict):

    user_message = data.get("message", "")
    session_id = data.get("session_id", "demo-session")

    if not isinstance(user_message, str) or not user_message.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid customer message."
        )

    user_message = user_message.strip()

    state = conversation_states.setdefault(session_id, {})

    # STEP 1: Handle customer resolution feedback

    if state.get("awaiting_resolution"):

        answer = user_message.lower().strip(" .!?")

        if answer in ["yes", "yes it did", "resolved", "it is resolved"]:

            state.clear()

            return {
                "reply": "That's great! I'm glad your issue has been resolved.",
                "conversation_status": "resolved",
                "response_source": "resolution_feedback"
            }

        elif answer in ["no", "no it didn't", "not resolved", "not yet"]:

            state["awaiting_resolution"] = False
            state["awaiting_details"] = True

            return {
                "reply": (
                    "I'm sorry that the suggested solution didn't resolve "
                    "your issue. Could you please explain what is still "
                    "going wrong? If necessary, I'll create a support ticket "
                    "for our human support team."
                ),
                "conversation_status": "awaiting_details",
                "response_source": "resolution_feedback"
            }

        else:

            return {
                "reply": (
                    "Please answer Yes or No. "
                    "Did the suggested solution resolve your issue?"
                ),
                "conversation_status": "awaiting_resolution",
                "response_source": "resolution_feedback"
            }

    # STEP 2: Receive additional details and create a ticket

    if state.get("awaiting_details"):

        original_message = state.get("original_message", "")

        combined_message = (
            original_message
            + ". Additional details: "
            + user_message
        )

        result = classify_complaint(combined_message)

        try:
            ticket_id = create_support_ticket(
                customer_message=combined_message,
                intent=result["intent"],
                session_id=session_id
            )

        except Exception as exc:
            print(f"Ticket creation failed: {exc}")

            raise HTTPException(
                status_code=500,
                detail="Unable to create your support ticket. Please try again."
            )

        state.clear()

        return {
            "reply": (
                "Your issue requires assistance from our human support team. "
                f"I have created a support ticket for you. "
                f"Your ticket ID is {ticket_id}. "
                "Our support team will review your complaint."
            ),
            "ticket_created": True,
            "ticket_id": ticket_id,
            "intent": result["intent"],
            "conversation_status": "ticket_created",
            "response_source": "automatic_ticket_creation"
        }

    # STEP 3: Classify complaint using BERT

    result = classify_complaint(user_message)

    # STEP 4: Search historical solved tickets

    historical_match = retrieve_solution(
        user_message,
        result["intent"]
    )

    # STEP 5: Generate chatbot response

    if historical_match:

        support_reply = (
            "I found a previously solved issue similar to yours.\n\n"
            f"Suggested solution:\n{historical_match['solution']}\n\n"
            "Did this resolve your issue?"
        )

        source = "historical_knowledge_base"

    else:

        support_reply = generate_support_response(
            result["intent"],
            user_message
        )

        support_reply += "\n\nDid this resolve your issue?"

        source = "existing_support_response"

    # Ask for resolution feedback in both cases

    state["awaiting_resolution"] = True
    state["original_message"] = user_message

    return {
        "user_message": user_message,
        "reply": support_reply,
        "intent": result["intent"],
        "confidence": result["confidence"],
        "historical_match": historical_match is not None,
        "matched_ticket": historical_match,
        "response_source": source,
        "conversation_status": "awaiting_resolution"
    }


# Register application routes

app.include_router(image_router)
app.include_router(ticket_router)

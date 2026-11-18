
"""Application entry point for the helpdesk backend."""

import uuid
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from routes.image import router as image_router
from routes.ticket_routes import router as ticket_router

from services.ticket_retrieval_service import retrieve_solution
from services.complaint_service import classify_complaint
from services.response_service import generate_support_response
from services.llm_service import generate_llm_response

from database.database import SessionLocal
from database.models import Ticket


app = FastAPI(title="AI Helpdesk Bot")

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
    allow_headers=["*"]
)


@app.get("/")
def home():
    return {"message": "AI Helpdesk Backend is running!"}


def create_support_ticket(
    customer_message,
    additional_details,
    customer_email,
    intent,
    session_id
):
    """Create a ticket after collecting all customer information."""

    db = SessionLocal()

    try:
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

        return ticket.ticket_id

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def wants_human_support(message):
    """Detect explicit requests for human support."""

    message = message.lower().strip()

    request_phrases = [
        "create a ticket",
        "raise a ticket",
        "need to raise a ticket",
        "open a ticket",
        "support ticket",
        "human agent",
        "talk to an agent",
        "speak to an agent",
        "talk to a human",
        "speak to a human",
        "human support",
        "contact support team",
        "contact customer support",
        "contact customer support team",
        "customer support team",
        "connect me to support",
        "connect me with support",
        "need customer support",
        "want customer support",
        "want to contact support",
        "want to contact customer support",
        "need to contact support",
        "need to contact customer support",
        "talk to customer support",
        "speak to customer support",
        "connect me to a human"
    ]

    return any(phrase in message for phrase in request_phrases)


def valid_email(email):
    """Validate customer email format."""

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return re.match(pattern, email) is not None


def save_history(history, user_message, reply):
    history.append({
        "role": "user",
        "content": user_message
    })

    history.append({
        "role": "assistant",
        "content": reply
    })

    return history[-20:]


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
    history = state.setdefault("history", [])

    # ------------------------------------------------
    # STEP 1: Handle an ongoing ticket collection flow.
    # ------------------------------------------------

    pending_ticket = state.get("pending_ticket")

    if pending_ticket:

        current_step = pending_ticket["step"]

        # Collect additional complaint details.
        if current_step == "additional_details":

            pending_ticket["additional_details"] = user_message
            pending_ticket["step"] = "customer_email"

            reply = (
                "Thank you for explaining your issue. "
                "Could you please provide your email address? "
                "Our support team will use it to send you ticket updates."
            )

            state["history"] = save_history(
                history,
                user_message,
                reply
            )

            return {
                "reply": reply,
                "ticket_created": False,
                "awaiting_email": True,
                "conversation_status": "collecting_customer_email"
            }

        # Collect and validate customer email.
        if current_step == "customer_email":

            email = user_message.strip()

            if not valid_email(email):

                reply = (
                    "That doesn't appear to be a valid email address. "
                    "Please enter a valid email address."
                )

                state["history"] = save_history(
                    history,
                    user_message,
                    reply
                )

                return {
                    "reply": reply,
                    "ticket_created": False,
                    "awaiting_email": True,
                    "conversation_status": "collecting_customer_email"
                }

            # Create ticket only after collecting all information.
            try:

                ticket_id = create_support_ticket(
                    customer_message=pending_ticket["original_complaint"],
                    additional_details=pending_ticket["additional_details"],
                    customer_email=email,
                    intent=pending_ticket["intent"],
                    session_id=session_id
                )

            except Exception as exc:

                print(f"Ticket creation failed: {exc}")

                raise HTTPException(
                    status_code=500,
                    detail="Unable to create your ticket. Please try again."
                )

            state.pop("pending_ticket", None)

            reply = (
                "Thank you! Your support ticket has been successfully created.\n\n"
                f"Ticket ID: {ticket_id}\n"
                f"Registered email: {email}\n\n"
                "Our human support team will review your complaint "
                "and send updates to your email address."
            )

            state["history"] = save_history(
                history,
                user_message,
                reply
            )

            return {
                "reply": reply,
                "ticket_created": True,
                "ticket_id": ticket_id,
                "conversation_status": "ticket_created",
                "response_source": "automatic_ticket_creation"
            }

    # ------------------------------------------------
    # STEP 2: Classify the customer's message.
    # ------------------------------------------------

    result = classify_complaint(user_message)
    intent = result["intent"]

    # ------------------------------------------------
    # STEP 3: Detect requests for human support.
    # ------------------------------------------------

    if wants_human_support(user_message):

        original_complaint = state.get(
            "last_customer_complaint",
            user_message
        )

        original_intent = state.get(
            "last_customer_intent",
            intent
        )

        state["pending_ticket"] = {
            "original_complaint": original_complaint,
            "additional_details": "",
            "intent": original_intent,
            "step": "additional_details"
        }

        reply = (
            "I'd be happy to connect you with our human support team.\n\n"
            "Before creating your ticket, could you please explain "
            "your issue in more detail? Please include your order "
            "number or any other relevant information."
        )

        state["history"] = save_history(
            history,
            user_message,
            reply
        )

        return {
            "reply": reply,
            "ticket_created": False,
            "conversation_status": "collecting_additional_details",
            "response_source": "ticket_information_collection"
        }

    # ------------------------------------------------
    # STEP 4: Normal conversation and support handling.
    # ------------------------------------------------

    historical_match = retrieve_solution(
        user_message,
        intent
    )

    context = ""

    if historical_match:
        context = historical_match.get("solution", "")

    try:

        support_reply = generate_llm_response(
            customer_message=user_message,
            intent=intent,
            context=context,
            conversation_history=history
        )

        source = "gemini_llm"

    except Exception as exc:

        print(f"Gemini response generation failed: {exc}")

        if historical_match:

            support_reply = (
                "I found a previously solved issue similar to yours.\n\n"
                f"Suggested solution:\n{historical_match['solution']}"
            )

            source = "historical_knowledge_base"

        else:

            support_reply = generate_support_response(
                intent,
                user_message
            )

            source = "existing_support_response"

    # Remember the customer's original complaint.
    state["last_customer_complaint"] = user_message
    state["last_customer_intent"] = intent

    state["history"] = save_history(
        history,
        user_message,
        support_reply
    )

    print("RESPONSE SOURCE:", source)

    return {
        "user_message": user_message,
        "reply": support_reply,
        "intent": intent,
        "confidence": result["confidence"],
        "historical_match": historical_match is not None,
        "matched_ticket": historical_match,
        "response_source": source,
        "conversation_status": "conversation_active"
    }


app.include_router(image_router)
app.include_router(ticket_router)

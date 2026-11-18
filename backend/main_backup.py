"""Application entry point for the AI Helpdesk backend."""

import re
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from routes.image import router as image_router
from routes.ticket_routes import router as ticket_router

from services.ticket_retrieval_service import retrieve_solution
from services.complaint_service import classify_complaint
from services.duplicate_ticket_service import detect_duplicate_ticket
from services.human_intervention_service import classify_human_intervention
from services.response_service import generate_support_response
from services.llm_service import (
    classify_conversation_turn,
    generate_llm_response,
)

from database.database import SessionLocal
from database.models import Ticket


app = FastAPI(title="AI Helpdesk Bot")

# Conversation state is currently stored in memory. For production, move this
# to a persistent store such as Redis or the database.
conversation_states = {}


# ------------------------------------------------
# CORS CONFIGURATION
# ------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "AI Helpdesk Backend is running!"}


# ------------------------------------------------
# SMALL HELPERS
# ------------------------------------------------

def is_small_talk(message):
    """Identify very short greetings and acknowledgements."""
    normalized = message.lower().strip().rstrip("!.,?")

    small_talk_messages = {
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "how are you doing",
        "thanks",
        "thank you",
        "thank you so much",
        "ok",
        "okay",
    }

    return normalized in small_talk_messages


def valid_email(email):
    """Validate customer email format."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return isinstance(email, str) and re.match(pattern, email) is not None


def save_history(history, user_message, reply):
    """Append a user/assistant exchange and retain the latest 20 messages."""
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    return history[-20:]


def create_support_ticket(
    customer_message,
    additional_details,
    customer_email,
    intent,
    session_id,
):
    """Create a ticket in the configured database."""
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
            status="Open",
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
    """Detect common explicit requests for a human support representative."""
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
        "connect me to a human",
    ]
    return any(phrase in message for phrase in request_phrases)


def _save_and_return(state, history, user_message, reply, **payload):
    """Save the exchange and return a consistent chatbot response."""
    state["history"] = save_history(history, user_message, reply)
    return {"reply": reply, **payload}


def _classify_issue(issue_text):
    """Run the existing BERT intent and human-intervention classifiers."""
    intent_result = classify_complaint(issue_text)
    try:
        intervention_result = classify_human_intervention(issue_text)
    except Exception as exc:
        print(f"Human intervention classification failed: {exc}")
        raise HTTPException(
            status_code=503,
            detail=(
                "We are temporarily unable to assess your request. "
                "Please try again later or contact human support."
            ),
        )

    return intent_result, intervention_result


def _start_ticket_collection(
    state,
    history,
    user_message,
    complaint,
    intent,
    intervention,
    intervention_confidence,
    reply,
):
    """Store ticket details and ask the customer for any missing information."""
    state["pending_ticket"] = {
        "original_complaint": complaint,
        "additional_details": "",
        "intent": intent,
        "intervention": intervention,
        "intervention_confidence": intervention_confidence,
        "step": "additional_details",
    }
    return _save_and_return(
        state,
        history,
        user_message,
        reply,
        ticket_created=False,
        intervention=intervention,
        intervention_confidence=intervention_confidence,
        conversation_status="collecting_additional_details",
        response_source="ticket_information_collection",
    )


def _check_duplicate_ticket(pending_ticket, email):
    """Return a duplicate match, if one exists."""
    db = SessionLocal()
    try:
        return detect_duplicate_ticket(
            db=db,
            customer_message=pending_ticket["original_complaint"],
            intent=pending_ticket["intent"],
            additional_details=pending_ticket.get("additional_details", ""),
            customer_email=email,
        )
    finally:
        db.close()


def _finish_ticket_creation(state, history, user_message, session_id, pending_ticket):
    """Check for duplicates and create the ticket when appropriate."""
    email = pending_ticket["customer_email"]

    if not pending_ticket.get("force_new_ticket"):
        try:
            duplicate = _check_duplicate_ticket(pending_ticket, email)
        except Exception as exc:
            print(f"Duplicate detection failed: {exc}")
            raise HTTPException(
                status_code=503,
                detail="Unable to verify existing tickets. Please try again.",
            )

        if duplicate:
            state["duplicate_confirmation"] = {
                "ticket_id": duplicate["ticket_id"]
            }
            reply = (
                "We found a similar unresolved support ticket.\n\n"
                f"Existing Ticket ID: {duplicate['ticket_id']}\n"
                f"Similarity: {duplicate['similarity']}\n\n"
                "Is this the same issue you have already reported?\n\n"
                "Reply YES to use the existing ticket, "
                "or NO to create a new ticket."
            )
            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                duplicate_found=True,
                existing_ticket_id=duplicate["ticket_id"],
                similarity=duplicate["similarity"],
                awaiting_duplicate_confirmation=True,
                conversation_status="awaiting_duplicate_confirmation",
            )

    try:
        ticket_id = create_support_ticket(
            customer_message=pending_ticket["original_complaint"],
            additional_details=pending_ticket.get("additional_details", ""),
            customer_email=email,
            intent=pending_ticket["intent"],
            session_id=session_id,
        )
    except Exception as exc:
        print(f"Ticket creation failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to create your ticket. Please try again.",
        )

    intervention = pending_ticket["intervention"]
    intervention_confidence = pending_ticket["intervention_confidence"]

    state.pop("pending_ticket", None)
    state.pop("duplicate_confirmation", None)
    state.pop("pending_ticket", None)
    state.pop("issue_messages", None)

    reply = (
        "Thank you! Your support ticket has been successfully created.\n\n"
        f"Ticket ID: {ticket_id}\n"
        f"Registered email: {email}\n\n"
        "Our human support team will review your complaint "
        "and send updates to your email address."
    )

    return _save_and_return(
        state,
        history,
        user_message,
        reply,
        ticket_created=True,
        ticket_id=ticket_id,
        intervention=intervention,
        intervention_confidence=intervention_confidence,
        conversation_status="ticket_created",
        response_source="automatic_ticket_creation",
    )


# ------------------------------------------------
# CHAT ENDPOINT
# ------------------------------------------------

@app.post("/chat")
def chat(data: dict):
    user_message = data.get("message", "")
    session_id = data.get("session_id", "demo-session")

    if not isinstance(user_message, str) or not user_message.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid customer message.",
        )

    user_message = user_message.strip()
    state = conversation_states.setdefault(session_id, {})
    history = state.setdefault("history", [])

    # ------------------------------------------------
    # STEP 1: HANDLE DUPLICATE CONFIRMATION
    # ------------------------------------------------

    duplicate_confirmation = state.get("duplicate_confirmation")
    if duplicate_confirmation:
        choice = user_message.lower().strip()

        if choice in {"yes", "y", "same", "same issue", "existing ticket"}:
            existing_ticket_id = duplicate_confirmation["ticket_id"]
            state.pop("duplicate_confirmation", None)
            state.pop("pending_ticket", None)

            reply = (
                "We found an existing support ticket for a similar issue.\n\n"
                f"Ticket ID: {existing_ticket_id}\n\n"
                "Our support team can continue handling your issue "
                "through this existing ticket."
            )
            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                duplicate_found=True,
                existing_ticket_id=existing_ticket_id,
                conversation_status="existing_ticket_referenced",
            )

        if choice in {"no", "n", "different", "different issue", "new ticket"}:
            state.pop("duplicate_confirmation", None)
            pending_ticket = state.get("pending_ticket")
            if pending_ticket:
                pending_ticket["force_new_ticket"] = True
                # The email has already been collected. Create the new ticket now.
                return _finish_ticket_creation(
                    state, history, user_message, session_id, pending_ticket
                )

        reply = (
            "Please reply YES if this is the same issue, "
            "or NO if this is a different issue and you need a new ticket."
        )
        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            duplicate_found=True,
            awaiting_duplicate_confirmation=True,
            conversation_status="awaiting_duplicate_confirmation",
        )

    # ------------------------------------------------
    # STEP 2: HANDLE ONGOING TICKET INFORMATION COLLECTION
    # ------------------------------------------------

    pending_ticket = state.get("pending_ticket")
    if pending_ticket:
        current_step = pending_ticket["step"]

        if current_step == "additional_details":
            # If the customer already explained the complaint, accept an email
            # entered immediately instead of accidentally saving it as details.
            if pending_ticket.get("original_complaint") and valid_email(user_message):
                pending_ticket["customer_email"] = user_message
                pending_ticket["step"] = "customer_email"
                return _finish_ticket_creation(
                    state, history, user_message, session_id, pending_ticket
                )

            if not pending_ticket.get("original_complaint"):
                if valid_email(user_message):
                    reply = (
                        "I have your email address. Could you first describe "
                        "the issue you need help with?"
                    )
                    return _save_and_return(
                        state,
                        history,
                        user_message,
                        reply,
                        ticket_created=False,
                        awaiting_complaint=True,
                        conversation_status="collecting_complaint",
                    )

                pending_ticket["original_complaint"] = user_message
                try:
                    intent_result, intervention_result = _classify_issue(user_message)
                except Exception as exc:
                    print(f"Complaint classification failed: {exc}")
                    raise HTTPException(
                        status_code=503,
                        detail="Unable to classify your complaint. Please try again.",
                    )

                pending_ticket["intent"] = intent_result["intent"]
                pending_ticket["intervention"] = intervention_result["intervention"]
                pending_ticket["intervention_confidence"] = intervention_result[
                    "confidence"
                ]
                pending_ticket["additional_details"] = ""
            else:
                pending_ticket["additional_details"] = user_message

            pending_ticket["step"] = "customer_email"
            reply = (
                "Thank you for explaining your issue. Could you please provide "
                "your email address? Our support team will use it to send "
                "you ticket updates."
            )
            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                awaiting_email=True,
                intervention=pending_ticket["intervention"],
                intervention_confidence=pending_ticket["intervention_confidence"],
                conversation_status="collecting_customer_email",
            )

        if current_step == "customer_email":
            email = user_message.strip()
            if not valid_email(email):
                reply = (
                    "That doesn't appear to be a valid email address. "
                    "Please enter a valid email address."
                )
                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    awaiting_email=True,
                    conversation_status="collecting_customer_email",
                )

            pending_ticket["customer_email"] = email
            return _finish_ticket_creation(
                state, history, user_message, session_id, pending_ticket
            )

    # ------------------------------------------------
    # STEP 3: UNDERSTAND THE CONVERSATION BEFORE CLASSIFYING A COMPLAINT
    # ------------------------------------------------

    conversation_context = {
        "last_customer_complaint": state.get("last_customer_complaint", ""),
        "issue_messages": state.get("issue_messages", []),
    }

    try:
        turn_result = classify_conversation_turn(
            customer_message=user_message,
            conversation_history=history,
            conversation_state=conversation_context,
        )
    except Exception as exc:
        print(f"Conversation understanding failed: {exc}")
        raise HTTPException(
            status_code=503,
            detail=(
                "I'm having trouble understanding your message right now. "
                "Please try again in a moment."
            ),
        )

    category = str(turn_result.get("category", "UNCERTAIN")).upper()
    print("CONVERSATION CATEGORY:", category)
    print("CONVERSATION REASON:", turn_result.get("reason", ""))

    # ------------------------------------------------
    # STEP 4: NORMAL CHAT DOES NOT ENTER THE TICKET PIPELINE
    # ------------------------------------------------

    if category in {"SMALL_TALK", "GENERAL_QUESTION", "PRODUCT_ENQUIRY"}:
        # A short greeting/thanks can be handled directly without running
        # complaint classifiers, RAG retrieval, or ticket creation.
        if category == "SMALL_TALK" or is_small_talk(user_message):
            reply = (
                "Hello! I'm doing well, thank you. How can I help you today?"
                if user_message.lower().strip().startswith(("hi", "hello", "hey"))
                else "You're welcome! Is there anything else I can help you with?"
            )
            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                conversation_status="conversation_active",
                response_source="conversation_understanding",
            )

        try:
            reply = generate_llm_response(
                customer_message=user_message,
                intent="general_enquiry",
                context="",
                conversation_history=history,
            )
        except Exception as exc:
            print(f"Gemini general response generation failed: {exc}")
            reply = (
                "I can help with that. Could you share a little more detail "
                "so I can guide you accurately?"
            )

        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            conversation_status="conversation_active",
            response_source="gemini_conversation",
        )

    # ------------------------------------------------
    # STEP 5: ASK FOR CLARIFICATION WHEN THE MESSAGE IS UNCLEAR
    # ------------------------------------------------

    if category == "UNCERTAIN":
        clarification = turn_result.get("clarification_question")
        if not clarification:
            clarification = (
                "Could you explain what you need help with? "
                "I'll guide you from there."
            )
        return _save_and_return(
            state,
            history,
            user_message,
            clarification,
            ticket_created=False,
            needs_clarification=True,
            conversation_status="awaiting_clarification",
            response_source="conversation_understanding",
        )

    # ------------------------------------------------
    # STEP 6: IDENTIFY THE ACTUAL COMPLAINT / FOLLOW-UP
    # ------------------------------------------------

    if category in {"CUSTOMER_ISSUE", "FOLLOW_UP_ISSUE"}:
        if category == "CUSTOMER_ISSUE" or not state.get("issue_messages"):
            state["issue_messages"] = [user_message]
        else:
            state["issue_messages"].append(user_message)

        # Keep the issue context bounded to avoid growing the prompt forever.
        state["issue_messages"] = state["issue_messages"][-8:]
        issue_text = " ".join(state["issue_messages"])

        # Keep the BERT input grounded in the customer's actual wording.
        try:
            intent_result, intervention_result = _classify_issue(issue_text)
        except Exception as exc:
            print(f"Issue classification failed: {exc}")
            raise HTTPException(
                status_code=503,
                detail="Unable to classify your complaint. Please try again.",
            )

        intent = intent_result["intent"]
        intervention = intervention_result["intervention"]
        intervention_confidence = intervention_result["confidence"]

        state["last_customer_complaint"] = issue_text
        state["last_customer_intent"] = intent
        state["last_intervention"] = intervention
        state["last_intervention_confidence"] = intervention_confidence

    elif category == "HUMAN_SUPPORT_REQUEST":
        # A request for a person is not itself the complaint. Reuse the
        # complaint already described in this conversation when available.
        issue_text = state.get("last_customer_complaint")
        if not issue_text:
            reply = (
                "Of course. I can connect you with our human support team. "
                "Could you briefly describe the issue you need help with?"
            )
            state["pending_ticket"] = {
                "original_complaint": None,
                "additional_details": "",
                "intent": "general_enquiry",
                "intervention": "HUMAN_ONLY",
                "intervention_confidence": 1.0,
                "step": "additional_details",
            }
            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                conversation_status="collecting_complaint",
                response_source="ticket_information_collection",
            )

        intent_result, intervention_result = _classify_issue(issue_text)
        intent = intent_result["intent"]
        intervention = intervention_result["intervention"]
        intervention_confidence = intervention_result["confidence"]

    else:
        # Unknown categories must not be treated as complaints by default.
        reply = (
            "Could you tell me a little more about what you need help with?"
        )
        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            needs_clarification=True,
            conversation_status="awaiting_clarification",
        )

    # ------------------------------------------------
    # STEP 7: EXPLICIT REQUEST FOR HUMAN SUPPORT
    # ------------------------------------------------

    explicit_human_request = (
        category == "HUMAN_SUPPORT_REQUEST" or wants_human_support(user_message)
    )

    if explicit_human_request:
        original_complaint = state.get("last_customer_complaint")
        if not original_complaint:
            original_complaint = issue_text if category in {
                "CUSTOMER_ISSUE",
                "FOLLOW_UP_ISSUE",
            } else None

        reply = (
            "I'd be happy to connect you with our human support team. "
            "Could you provide any additional details, such as your order "
            "number, that may help our team investigate?"
        )
        return _start_ticket_collection(
            state,
            history,
            user_message,
            original_complaint,
            intent,
            intervention,
            intervention_confidence,
            reply,
        )

    # ------------------------------------------------
    # STEP 8: HUMAN-REQUIRED COMPLAINTS GO TO TICKET COLLECTION
    # ------------------------------------------------

    if intervention in {"AI_ASSISTED_HUMAN_REQUIRED", "HUMAN_ONLY"}:
        if intervention == "AI_ASSISTED_HUMAN_REQUIRED":
            reply = (
                "I can help with general information about this issue, but "
                "completing your request requires assistance from our human "
                "support team.\n\n"
                "Let's create a support ticket so our team can help you. "
                "Could you provide any additional details, such as your "
                "order number?"
            )
        else:
            reply = (
                "This issue requires direct assistance from our human "
                "support team. I will help you create a support ticket "
                "so that our team can investigate it.\n\n"
                "Could you please provide any additional details about "
                "the issue?"
            )

        return _start_ticket_collection(
            state,
            history,
            user_message,
            issue_text,
            intent,
            intervention,
            intervention_confidence,
            reply,
        )

    # ------------------------------------------------
    # STEP 9: AI-RESOLVABLE ISSUES USE HISTORICAL RAG + GEMINI
    # ------------------------------------------------

    if intervention != "AI_RESOLVABLE":
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to safely classify this request "
                "for automatic resolution."
            ),
        )

    try:
        historical_match = retrieve_solution(issue_text, intent)
    except Exception as exc:
        print(f"Historical ticket retrieval failed: {exc}")
        historical_match = None

    context = historical_match.get("solution", "") if historical_match else ""

    try:
        support_reply = generate_llm_response(
            customer_message=issue_text,
            intent=intent,
            context=context,
            conversation_history=history,
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
            support_reply = generate_support_response(intent, issue_text)
            source = "existing_support_response"

    state["history"] = save_history(history, user_message, support_reply)

    print("INTENT:", intent)
    print("INTERVENTION:", intervention)
    print("INTERVENTION CONFIDENCE:", intervention_confidence)
    print("RESPONSE SOURCE:", source)

    return {
        "user_message": user_message,
        "reply": support_reply,
        "intent": intent,
        "intent_confidence": intent_result["confidence"],
        "intervention": intervention,
        "intervention_confidence": intervention_confidence,
        "historical_match": historical_match is not None,
        "matched_ticket": historical_match,
        "ticket_created": False,
        "response_source": source,
        "conversation_status": "conversation_active",
    }


# ------------------------------------------------
# REGISTER ROUTERS
# ------------------------------------------------

app.include_router(image_router)
app.include_router(ticket_router)

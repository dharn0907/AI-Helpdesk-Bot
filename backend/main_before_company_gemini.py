"""Application entry point for the AI Helpdesk backend."""

import re
import uuid

from fastapi import FastAPI, HTTPException
from services.first_level_intent_service import classify_first_level_intent
from services.business_intent_service import classify_business_intent
from fastapi.middleware.cors import CORSMiddleware

from routes.image import router as image_router
from routes.ticket_routes import router as ticket_router
from routes.company_routes import router as company_router

from services.ticket_retrieval_service import retrieve_solution
from services.complaint_service import classify_complaint
from services.duplicate_ticket_service import detect_duplicate_ticket
from services.human_intervention_service import classify_human_intervention
from services.response_service import generate_support_response
from services.llm_service import (
    classify_conversation_turn,
    generate_llm_response,
)
from services.ticket_conversation_service import (
    interpret_ticket_message,
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


def is_ticket_cancellation(message):
    """Recognize clear natural-language requests to cancel a pending ticket."""
    normalized = re.sub(r"[^a-z0-9' ]+", " ", message.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    normalized = normalized.replace("don't", "do not")
    normalized = normalized.replace("doesn't", "does not")
    normalized = normalized.replace("didn't", "did not")

    cancellation_phrases = (
        "cancel",
        "cancel ticket",
        "cancel the ticket",
        "stop this ticket",
        "stop the ticket",
        "forget it",
        "never mind",
        "nevermind",
        "do not create a ticket",
        "do not raise a ticket",
        "do not need a ticket",
        "do not need to raise a ticket",
        "do not want a ticket",
        "do not want to raise a ticket",
        "i do not need a ticket",
        "i do not need to raise a ticket",
        "i do not want a ticket",
        "i do not want to raise a ticket",
        "i don't need a ticket",
        "i don't need to raise a ticket",
        "i don't want a ticket",
        "i don't want to raise a ticket",
        "no need to create a ticket",
        "no need to raise a ticket",
        "leave it",
    )

    return any(
        phrase in normalized
        for phrase in cancellation_phrases
    )


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
        "detail_messages": [],
        "issue_summary": complaint or "",
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


def _ticket_additional_details_for_storage(pending_ticket):
    """Combine raw customer details and the confirmed issue summary."""
    sections = []

    details = pending_ticket.get("additional_details", "").strip()
    summary = pending_ticket.get("issue_summary", "").strip()

    if details:
        sections.append(
            "Additional customer-provided details:\n" + details
        )

    if summary:
        sections.append(
            "Confirmed issue summary:\n" + summary
        )

    return "\n\n".join(sections)


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
            additional_details=_ticket_additional_details_for_storage(pending_ticket),
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

    # Handle clear cancellation requests from any active ticket state.
    if state.get("pending_ticket") and is_ticket_cancellation(user_message):
        state.pop("pending_ticket", None)
        state.pop("duplicate_confirmation", None)

        reply = (
            "No problem. I've cancelled your pending support request. "
            "No new ticket has been created."
        )

        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            conversation_status="ticket_cancelled",
        )

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
        current_step = pending_ticket.get("step", "additional_details")

        # Ensure older pending conversations have the new fields.
        pending_ticket.setdefault("additional_details", "")
        pending_ticket.setdefault("detail_messages", [])
        pending_ticket.setdefault(
            "issue_summary",
            pending_ticket.get("original_complaint") or "",
        )

        # --------------------------------------------
        # A. Collect and interpret issue details
        # --------------------------------------------

        if current_step == "additional_details":
            try:
                interpretation = interpret_ticket_message(
                    customer_message=user_message,
                    pending_ticket=pending_ticket,
                    conversation_history=history[-10:],
                )
            except Exception as exc:
                print(f"Ticket message interpretation failed: {exc}")
                interpretation = {
                    "action": "UNCERTAIN",
                    "confidence": 0.0,
                    "relevant_details": "",
                    "issue_summary": "",
                    "needs_clarification": True,
                    "clarification_question": (
                        "Could you clarify how this message relates "
                        "to the support issue?"
                    ),
                }

            action = interpretation.get("action", "UNCERTAIN")
            confidence = interpretation.get("confidence", 0.0)

            # Do not accept uncertain model interpretations as facts.
            if confidence < 0.65:
                action = "UNCERTAIN"

            if action == "ADD_DETAIL":
                relevant_detail = (
                    interpretation.get("relevant_details") or ""
                ).strip()

                if not relevant_detail:
                    action = "UNCERTAIN"
                else:
                    # The first customer explanation becomes the complaint.
                    if not pending_ticket.get("original_complaint"):
                        pending_ticket["original_complaint"] = relevant_detail

                        try:
                            intent_result, intervention_result = (
                                _classify_issue(relevant_detail)
                            )
                        except Exception as exc:
                            print(f"Complaint classification failed: {exc}")
                            raise HTTPException(
                                status_code=503,
                                detail=(
                                    "Unable to classify your complaint. "
                                    "Please try again."
                                ),
                            )

                        pending_ticket["intent"] = intent_result["intent"]
                        pending_ticket["intervention"] = (
                            intervention_result["intervention"]
                        )
                        pending_ticket["intervention_confidence"] = (
                            intervention_result["confidence"]
                        )
                    else:
                        pending_ticket["detail_messages"].append(
                            relevant_detail
                        )
                        pending_ticket["additional_details"] = "\n".join(
                            pending_ticket["detail_messages"]
                        )

                    new_summary = (
                        interpretation.get("issue_summary") or ""
                    ).strip()

                    if new_summary:
                        pending_ticket["issue_summary"] = new_summary

                    # Generate a natural, context-aware response for this
                    # specific detail instead of repeating a fixed message.
                    try:
                        reply = generate_llm_response(
                            customer_message=user_message,
                            intent="customer_issue",
                            context=(
                                "The customer is currently explaining an "
                                "existing support issue. Their latest detail "
                                "has already been understood and saved.\n"
                                f"Original complaint: "
                                f"{pending_ticket.get('original_complaint', '')}\n"
                                f"Additional details so far: "
                                f"{pending_ticket.get('additional_details', '')}\n"
                                f"Current issue summary: "
                                f"{pending_ticket.get('issue_summary', '')}\n\n"
                                "Respond naturally to the latest detail. "
                                "Acknowledge what the customer actually said. "
                                "Ask at most one useful follow-up question if "
                                "more information would help. Do not ask for "
                                "details already provided. Do not restart the "
                                "conversation or claim a ticket was created. "
                                "Make it clear that the customer can say "
                                "'I'm done' when they have finished explaining "
                                "the issue and are ready to review the summary."
                            ),
                            conversation_history=history,
                        )

                        reply = (reply or "").strip()
                        if not reply:
                            raise ValueError("Gemini returned an empty response.")

                    except Exception as exc:
                        print(f"Conversational response generation failed: {exc}")
                        reply = (
                            "I've added that information to your support issue. "
                            "Is there anything else you'd like to mention? "
                            "You can say 'I'm done' whenever you've finished."
                        )

                    return _save_and_return(
                        state,
                        history,
                        user_message,
                        reply,
                        ticket_created=False,
                        awaiting_additional_details=True,
                        intervention=pending_ticket.get("intervention"),
                        intervention_confidence=pending_ticket.get(
                            "intervention_confidence"
                        ),
                        conversation_status="collecting_additional_details",
                    )

            if action == "SIDE_QUESTION":
                try:
                    reply = generate_llm_response(
                        customer_message=user_message,
                        intent="customer_support",
                        context=(
                            "The customer has an active support request but "
                            "has asked a separate question.\n"
                            "IMPORTANT: Answer the customer's latest question "
                            "as the MAIN priority. Give a complete, useful, "
                            "natural answer. Do not ignore the question or "
                            "replace its answer with a reminder about the "
                            "support issue.\n"
                            "You are an AI support assistant for this company. "
                            "If asked who you are, explain this honestly. "
                            "For general knowledge questions about sports, "
                            "technology, education, people, science, or other "
                            "topics, answer normally using your knowledge. "
                            "Do not claim that you cannot answer because you "
                            "are a support assistant. Do not invent facts.\n"
                            "After answering, you may add one short, natural "
                            "sentence acknowledging that the customer's "
                            "support request is still available. Do not force "
                            "the conversation back to it.\n"
                            "Preserve the existing pending ticket and all "
                            "collected details. Do not modify the issue "
                            "summary or details. Do not create, cancel, or "
                            "pause a ticket. Do not repeat questions that "
                            "have already been answered."
                        ),
                        conversation_history=history,
                    )
                    reply = (reply or "").strip()
                    if not reply:
                        raise ValueError("Gemini returned an empty response.")

                except Exception as exc:
                    print(f"Side-question response generation failed: {exc}")
                    reply = (
                        "I'm your AI support assistant. I can help answer "
                        "questions and guide you through your support request. "
                        "What would you like to add or correct?"
                    )

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    awaiting_additional_details=True,
                    conversation_status="collecting_additional_details",
                )

            if action == "GREETING":
                reply = (
                    "Hello! We can continue with your support request. "
                    "Please share any details about the issue, or say "
                    "'I'm done' if you have finished explaining it."
                )

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    conversation_status="collecting_additional_details",
                )

            if action == "UNRELATED":
                pending_ticket["step"] = "awaiting_ticket_direction"

                reply = (
                    "I noticed that this message may be about something "
                    "different from your current support issue. "
                    "Would you like to CONTINUE with the current issue, "
                    "PAUSE this support request, or CANCEL it?"
                )

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    awaiting_ticket_direction=True,
                    conversation_status="clarifying_ticket_context",
                )

            if action == "PAUSE":
                pending_ticket["step"] = "paused"

                reply = (
                    "No problem. Your support request is paused. "
                    "You can resume explaining the issue whenever "
                    "you are ready."
                )

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    conversation_status="ticket_paused",
                )

            if action == "CANCEL":
                state.pop("pending_ticket", None)

                reply = (
                    "Your current support request has been cancelled. "
                    "No new ticket has been created."
                )

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    conversation_status="ticket_cancelled",
                )

            if action == "COMPLETE":
                if not pending_ticket.get("original_complaint"):
                    reply = (
                        "Before I prepare a summary, could you describe "
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

                new_summary = (
                    interpretation.get("issue_summary") or ""
                ).strip()

                if new_summary:
                    pending_ticket["issue_summary"] = new_summary

                pending_ticket["step"] = "awaiting_summary_confirmation"

                summary = pending_ticket.get("issue_summary") or (
                    pending_ticket["original_complaint"]
                )

                reply = (
                    "Thank you. Here is the summary of your support issue:\n\n"
                    f"{summary}\n\n"
                    "Is this summary accurate? Please reply YES to confirm "
                    "or NO if you would like to make corrections."
                )

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    awaiting_summary_confirmation=True,
                    issue_summary=summary,
                    conversation_status="awaiting_summary_confirmation",
                )

            # UNCERTAIN or an unsupported action.
            clarification = (
                interpretation.get("clarification_question") or ""
            ).strip()

            if not clarification:
                clarification = (
                    "Could you clarify whether this message adds "
                    "information about your current support issue?"
                )

            return _save_and_return(
                state,
                history,
                user_message,
                clarification,
                ticket_created=False,
                awaiting_ticket_clarification=True,
                conversation_status="clarifying_ticket_context",
            )

        # --------------------------------------------
        # B. Clarify what to do with the current ticket
        # --------------------------------------------

        if current_step == "awaiting_ticket_direction":
            choice = user_message.strip().lower()
            choice = choice.strip(" .,!?")

            if choice in {
                "continue", "continue ticket", "current issue",
                "keep going", "yes", "resume"
            }:
                pending_ticket["step"] = "additional_details"

                reply = (
                    "Sure. Let's continue with your current support issue. "
                    "Please share the next relevant detail."
                )

                return _save_and_return(
                    state, history, user_message, reply,
                    ticket_created=False,
                    conversation_status="collecting_additional_details",
                )

            if choice in {"pause", "pause ticket", "later"}:
                pending_ticket["step"] = "paused"

                reply = (
                    "No problem. Your support request is paused. "
                    "Reply RESUME to continue or CANCEL to discard it."
                )

                return _save_and_return(
                    state, history, user_message, reply,
                    ticket_created=False,
                    conversation_status="ticket_paused",
                )

            if choice in {"cancel", "cancel ticket", "stop"}:
                state.pop("pending_ticket", None)

                reply = (
                    "Your support request has been cancelled. "
                    "No new ticket has been created."
                )

                return _save_and_return(
                    state, history, user_message, reply,
                    ticket_created=False,
                    conversation_status="ticket_cancelled",
                )

            try:
                reply = generate_llm_response(
                    customer_message=user_message,
                    intent="customer_support",
                    context=(
                        "The customer has an active pending support request. "
                        "They were asked whether to CONTINUE, PAUSE, or CANCEL, "
                        "but have now asked another question. Answer the latest "
                        "question directly and naturally, using general knowledge "
                        "when appropriate. Do not invent facts. After answering, "
                        "briefly remind them they can continue, pause, or cancel "
                        "their pending support request. Do not change ticket state "
                        "or claim a ticket was created."
                    ),
                    conversation_history=history,
                )
                reply = (reply or "").strip()
                if not reply:
                    raise ValueError("Empty Gemini response.")
            except Exception as exc:
                print(f"Side-question response failed: {exc}")
                reply = (
                    "I can help with that question. You can also choose "
                    "CONTINUE, PAUSE, or CANCEL for your support request."
                )

            return _save_and_return(
                state, history, user_message, reply,
                ticket_created=False,
                awaiting_ticket_direction=True,
                conversation_status="clarifying_ticket_context",
            )

        # --------------------------------------------
        # C. Confirm the issue summary
        # --------------------------------------------


        if current_step == "awaiting_summary_confirmation":
            choice = user_message.strip().lower()
            choice = choice.strip(" .,!")

            positive_choices = {
                "yes", "y", "yes confirm", "confirm",
                "correct", "looks good", "that's correct",
                "that is correct", "accurate",
            }

            negative_choices = {
                "no", "n", "nope", "incorrect",
                "not correct", "make corrections",
                "needs correction",
            }

            if choice in positive_choices:
                pending_ticket["step"] = "customer_email"

                reply = (
                    "Thank you for confirming the summary. "
                    "Please provide your email address so our support "
                    "team can send you ticket updates."
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

            if choice in negative_choices:
                pending_ticket["step"] = "additional_details"

                reply = (
                    "Of course. Please tell me what needs to be corrected "
                    "or added to the summary."
                )

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    awaiting_additional_details=True,
                    conversation_status="collecting_additional_details",
                )

            reply = (
                "Please reply YES to confirm the summary, "
                "or NO if you would like to correct it."
            )

            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                awaiting_summary_confirmation=True,
                conversation_status="awaiting_summary_confirmation",
            )

        # --------------------------------------------
        # C. Paused ticket
        # --------------------------------------------

        if current_step == "paused":
            choice = user_message.strip().lower()

            if choice in {"resume", "continue", "continue ticket", "yes"}:
                pending_ticket["step"] = "additional_details"

                reply = (
                    "Let's continue with your support request. "
                    "Please share the next detail about the issue."
                )

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    conversation_status="collecting_additional_details",
                )

            if choice in {"cancel", "cancel ticket", "stop"}:
                state.pop("pending_ticket", None)

                reply = (
                    "Your support request has been cancelled. "
                    "No new ticket has been created."
                )

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    conversation_status="ticket_cancelled",
                )

            reply = (
                "Your support request is still paused. "
                "Reply RESUME to continue or CANCEL to discard it."
            )

            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                conversation_status="ticket_paused",
            )

        # --------------------------------------------
        # D. Collect customer email after confirmation
        # --------------------------------------------

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
                state,
                history,
                user_message,
                session_id,
                pending_ticket,
            )

    # STEP 3: UNIVERSAL FIRST-LEVEL INTENT CLASSIFICATION
    # ------------------------------------------------

    CONFIDENCE_THRESHOLD = 0.75

    try:
        first_level_result = classify_first_level_intent(user_message)

        first_intent = first_level_result["intent"]
        first_confidence = first_level_result["confidence"]
        first_margin = first_level_result["margin"]
        first_uncertain = first_level_result["uncertain"]

        print("FIRST-LEVEL INTENT:", first_intent)
        print("FIRST-LEVEL CONFIDENCE:", first_confidence)
        print("FIRST-LEVEL MARGIN:", first_margin)
        print("FIRST-LEVEL UNCERTAIN:", first_uncertain)

    except Exception as exc:
        print(f"First-level classification failed: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Unable to understand your message right now. Please try again.",
        )

    # ------------------------------------------------
    # STEP 4: GEMINI FALLBACK OR SUPPORT CONVERSATION UNDERSTANDING
    # ------------------------------------------------

    conversation_context = {
        "last_customer_complaint": state.get("last_customer_complaint", ""),
        "issue_messages": state.get("issue_messages", []),
    }

    # Gemini is used when BERT is uncertain.
    # It is also used for support messages to identify follow-ups,
    # explicit human requests, and the actual conversation context.
    needs_gemini_understanding = (
        first_uncertain
        or first_intent == "CUSTOMER_SUPPORT"
    )

    if needs_gemini_understanding:
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
                detail="I'm having trouble understanding your message right now. Please try again.",
            )

        category = str(
            turn_result.get("category", "UNCERTAIN")
        ).upper()

        # Do not let an uncertain BERT prediction bypass Gemini's result.
        print("GEMINI CONVERSATION CATEGORY:", category)

    else:
        # High-confidence business and general messages are routed directly.
        category = {
            "BUSINESS_ENQUIRY": "PRODUCT_ENQUIRY",
            "GENERAL_QUERY": "GENERAL_QUESTION",
        }.get(first_intent, "UNCERTAIN")

    print("FINAL ROUTING CATEGORY:", category)

    # ------------------------------------------------
    # STEP 5: NORMAL CHAT AND BUSINESS ENQUIRIES
    # ------------------------------------------------

    if category in {"SMALL_TALK", "GENERAL_QUESTION", "PRODUCT_ENQUIRY"}:

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

        response_intent = (
            "business_enquiry"
            if category == "PRODUCT_ENQUIRY"
            else "general_enquiry"
        )

        business_context = ""

        if category == "PRODUCT_ENQUIRY":
            try:
                business_result = classify_business_intent(user_message)
                business_intent = business_result["intent"]
                business_confidence = business_result["confidence"]

                print("BUSINESS INTENT:", business_intent)
                print("BUSINESS INTENT CONFIDENCE:", business_confidence)

                business_context = (
                    f"Detected business enquiry category: {business_intent}. "
                    "Use this category to understand the customer's specific "
                    "business enquiry and answer accordingly. "
                    "Do not invent company-specific information."
                )
            except Exception as exc:
                print(f"Business intent classification failed: {exc}")
                business_context = (
                    "The message is a business enquiry, but its specific "
                    "category could not be determined."
                )

        try:
            reply = generate_llm_response(
                customer_message=user_message,
                intent=response_intent,
                context=business_context,
                conversation_history=history,
            )
        except Exception as exc:
            print(f"Gemini response generation failed: {exc}")
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
            response_source=(
                "gemini_business_enquiry"
                if category == "PRODUCT_ENQUIRY"
                else "gemini_conversation"
            ),
        )

    # ------------------------------------------------
    # STEP 6 CONTINUES WITH YOUR EXISTING SUPPORT LOGIC
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
    # ------------------------------------------------
    # STEP 8: PROFESSIONAL CONVERSATION FOR HUMAN-REQUIRED ISSUES
    # ------------------------------------------------

    if intervention in {"AI_ASSISTED_HUMAN_REQUIRED", "HUMAN_ONLY"}:

        if intervention == "AI_ASSISTED_HUMAN_REQUIRED":
            opening_context = (
                "This is the beginning of a customer support conversation. "
                "The customer's issue may need assistance beyond automated "
                "support, but do not announce a classification or immediately "
                "tell the customer to create a ticket.\n"
                "Acknowledge the problem naturally and try to understand "
                "the situation. Ask one specific, useful diagnostic question "
                "based on the customer's actual message. You may suggest "
                "a safe basic check when appropriate.\n"
                "Do not assume the cause or invent product information. "
                "Do not claim that the issue is resolved or that an action "
                "has been performed."
            )
        else:
            opening_context = (
                "This is the beginning of a customer support conversation "
                "about an issue that requires careful handling.\n"
                "Acknowledge the customer's concern professionally. "
                "Begin by understanding exactly what happened. Ask one "
                "specific question that helps clarify the issue and gather "
                "useful information.\n"
                "Do not expose internal classifications. Do not promise "
                "that you can resolve the issue automatically. Do not "
                "invent facts or claim that an action has been performed."
            )

        opening_context += (
            "\n\nIMPORTANT CONVERSATION STYLE:\n"
            "- Sound like a professional, helpful support representative.\n"
            "- Do not begin with 'This issue requires human assistance'.\n"
            "- Do not immediately announce ticket creation.\n"
            "- Avoid generic requests such as 'provide more details'.\n"
            "- Ask only ONE relevant question.\n"
            "- Never assume information the customer has not provided.\n"
            "- Be concise, natural and empathetic."
        )

        try:
            opening_reply = generate_llm_response(
                customer_message=issue_text,
                intent=intent,
                context=opening_context,
                conversation_history=history,
            )

            if not opening_reply or not opening_reply.strip():
                raise ValueError("Gemini returned an empty opening response.")

        except Exception as exc:
            print(f"Professional opening generation failed: {exc}")

            opening_reply = (
                "I'm sorry you're experiencing this problem. "
                "I'd like to understand what's happening so I can "
                "guide you through the next steps. "
                "Could you tell me what happens when you try?"
            )

        return _start_ticket_collection(
            state,
            history,
            user_message,
            issue_text,
            intent,
            intervention,
            intervention_confidence,
            opening_reply,
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
app.include_router(company_router)

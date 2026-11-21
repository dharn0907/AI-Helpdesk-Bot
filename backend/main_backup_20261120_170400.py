"""Application entry point for the AI Helpdesk backend."""

import re
import time

import uuid
from fastapi import FastAPI, HTTPException
from services.zep_memory_service import save_assistant_turn, start_user_turn
from services.first_level_intent_service import classify_first_level_intent
from services.business_intent_service import classify_business_intent
from fastapi.middleware.cors import CORSMiddleware
from routes.knowledge_base_routes import router as knowledge_base_router
from routes.image import router as image_router
from routes.ticket_routes import router as ticket_router
from services.conversation_logging_service import save_conversation_exchange
from routes.company_routes import router as company_router
from services.ticket_retrieval_service import (
    retrieve_solution,
    retrieve_approved_solution,
)
from services.complaint_service import classify_complaint
from services.duplicate_ticket_service import detect_duplicate_ticket
from services.human_intervention_service import classify_human_intervention
from services.response_service import generate_support_response
from database.database import Base, engine
from database.models import KnowledgeBaseFile, KnowledgeBaseRecord
from services.llm_service import (
    classify_conversation_turn,
    generate_llm_response as _generate_llm_response,
    plan_knowledge_retrieval,
    validate_company_domain,
)
from services.ticket_conversation_service import (
    interpret_ticket_message,
)
from routes.conversation_routes import router as conversation_router
from database.database import SessionLocal
from database.models import (
    Ticket,
    Company,
    BotConfiguration,
    Conversation,
    ConversationMessage,
    HistoricalSolutionFeedback,
)

def _get_active_company_config():
    """Load the active company's saved bot instructions for domain validation."""
    db = SessionLocal()
    try:
        company = (
            db.query(Company)
            .filter(Company.is_active.is_(True))
            .first()
        )
        if not company:
            return None

        configuration = (
            db.query(BotConfiguration)
            .filter(BotConfiguration.company_id == company.id)
            .first()
        )
        if not configuration:
            return None

        return {
            "company_name": company.name,
            "bot_name": configuration.bot_name or "",
            "what_this_bot_helps_with": configuration.what_this_bot_helps_with or "",
            "about_business": configuration.about_business or "",
            "how_to_respond": configuration.how_to_respond or "",
            "when_to_handoff": configuration.when_to_handoff or "",
            "dos": configuration.dos or "",
            "donts": configuration.donts or "",
            "advanced_instructions": configuration.advanced_instructions or "",
        }
    finally:
        db.close()


def _check_company_domain(issue_text, conversation_history=None):
    config = _get_active_company_config()
    if not config:
        return {"decision": "UNCERTAIN", "reason": "Company configuration unavailable"}

    return validate_company_domain(
        customer_message=issue_text,
        company_config=config,
        conversation_history=conversation_history,
    )


def _domain_rejection_message():
    return (
        "I'm sorry, but this issue appears to be outside the services "
        "this company's chatbot is configured to support. I can't create "
        "a support ticket for it. Please contact the relevant service "
        "provider for assistance."
    )






def generate_llm_response(
    customer_message: str,
    intent: str = "general_enquiry",
    context: str = "",
    conversation_history: list = None
) -> str:
    """
    Generate a response using company configuration and relevant
    company Knowledge Base information.
    """
    start_time = time.perf_counter()
    
    
    import json
    import re
    from collections import defaultdict

    db = SessionLocal()
    company_config = None
    knowledge_context = ""

    try:
        company = (
            db.query(Company)
            .filter(Company.is_active.is_(True))
            .first()
        )

        if company:
            configuration = (
                db.query(BotConfiguration)
                .filter(BotConfiguration.company_id == company.id)
                .first()
            )

            if configuration:
                company_config = {
                    "company_name": company.name,
                    "bot_name": configuration.bot_name,
                    "what_this_bot_helps_with": configuration.what_this_bot_helps_with or "",
                    "about_business": configuration.about_business or "",
                    "how_to_respond": configuration.how_to_respond or "",
                    "when_to_handoff": configuration.when_to_handoff or "",
                    "dos": configuration.dos or "",
                    "donts": configuration.donts or "",
                    "advanced_instructions": configuration.advanced_instructions or "",
                }

            records = (
                db.query(KnowledgeBaseRecord)
                .filter(KnowledgeBaseRecord.company_id == company.id)
                .all()
            )

            
            message = customer_message.lower()

            # Identify catalogue records without hardcoding product categories.
            product_catalogue_records = [
                record
                for record in records
                if (
                    (record.record_data or {}).get("Section_Title")
                    == "PRODUCT CATALOGUE AND SUGGESTED PRICE LIST"
                    and (record.record_data or {}).get("Row_Type") == "Field"
                    and (record.record_data or {}).get("Record")
                )
            ]

            if product_catalogue_records:
                available_product_groups = sorted({
                    str(record.record_data.get("Group", "")).upper()
                    for record in product_catalogue_records
                    if record.record_data.get("Group")
                })

                # Let Gemini understand the request and plan retrieval.
                try:
                    retrieval_plan = plan_knowledge_retrieval(
                        customer_message=customer_message,
                        available_product_groups=available_product_groups,
                        conversation_history=conversation_history
                    )
                except Exception as error:
                    print("PRODUCT RETRIEVAL PLANNER ERROR:", error)
                    retrieval_plan = {
                        "needs_product_catalogue": False,
                        "retrieval_scope": "none",
                        "product_groups": [],
                        "search_query": ""
                    }

                selected_catalogue_records = []
                retrieval_scope = retrieval_plan["retrieval_scope"]

                if retrieval_plan["needs_product_catalogue"]:

                    if retrieval_scope == "all_products":
                        selected_catalogue_records = product_catalogue_records

                    elif retrieval_scope == "groups":
                        requested_groups = set(
                            retrieval_plan["product_groups"]
                        )

                        selected_catalogue_records = [
                            record
                            for record in product_catalogue_records
                            if str(
                                record.record_data.get("Group", "")
                            ).upper() in requested_groups
                        ]

                    elif retrieval_scope == "search":
                        search_words = set(
                            re.findall(
                                r"[a-zA-Z0-9]+",
                                retrieval_plan["search_query"].lower()
                            )
                        )

                        product_scores = defaultdict(int)

                        for record in product_catalogue_records:
                            searchable_text = str(
                                record.search_text or ""
                            ).lower()

                            score = sum(
                                1 for word in search_words
                                if word in searchable_text
                            )

                            if score > 0:
                                data = record.record_data
                                product_key = (
                                    str(data.get("Group", "")).upper(),
                                    str(data.get("Record", ""))
                                )
                                product_scores[product_key] += score

                        top_product_keys = {
                            key
                            for key, score in sorted(
                                product_scores.items(),
                                key=lambda item: item[1],
                                reverse=True
                            )[:10]
                        }

                        selected_catalogue_records = [
                            record
                            for record in product_catalogue_records
                            if (
                                str(
                                    record.record_data.get("Group", "")
                                ).upper(),
                                str(record.record_data.get("Record", ""))
                            ) in top_product_keys
                        ]

                    # Reconstruct complete products from their SKU records.
                    grouped_products = defaultdict(dict)

                    for record in selected_catalogue_records:
                        data = record.record_data or {}

                        sku = str(data.get("Record", ""))
                        group = str(data.get("Group", "")).upper()
                        key = data.get("Key", "")
                        value = data.get("Value", "")

                        if key and value:
                            grouped_products[(group, sku)][key] = value

                    product_entries = []

                    for (group, sku), details in grouped_products.items():
                        details["SKU"] = sku
                        details["Product group"] = group
                        product_entries.append(details)

                    knowledge_context = (
                        "COMPANY PRODUCT CATALOGUE:\n"
                        "The following are complete product records "
                        "retrieved from the active company's catalogue.\n"
                        "Use the actual catalogue data to answer the "
                        "customer's question.\n"
                        "Compare numeric prices yourself when asked "
                        "for the cheapest or most expensive product.\n"
                        "Do not confuse Catalogue price with Starting price.\n"
                        "Do not invent products, prices, stock availability, "
                        "or live checkout prices.\n\n"
                        + (
                            json.dumps(
                                product_entries,
                                ensure_ascii=False,
                                indent=2
                            )
                            if product_entries
                            else "No matching products were found in the catalogue."
                        )
                    )

                    print(
                        "LLM-PLANNED PRODUCT RETRIEVAL:",
                        len(product_entries),
                        "products;",
                        "scope:",
                        retrieval_scope,
                        "groups:",
                        retrieval_plan["product_groups"],
                        "company:",
                        company.id
                    )

            # General knowledge fallback for questions outside the bat catalogue.
            if not knowledge_context and records:
                query_words = set(
                    re.findall(r"[a-zA-Z0-9]+", message)
                )

                stop_words = {
                    "the", "a", "an", "is", "are", "am", "do", "does",
                    "what", "which", "who", "where", "when", "how",
                    "you", "your", "i", "we", "have", "has", "can",
                    "could", "would", "please", "tell", "me", "show",
                    "give", "there", "this", "that", "of", "for",
                    "in", "on", "to", "with", "and", "or", "my"
                }

                query_words -= stop_words
                ranked_records = []

                for record in records:
                    searchable_text = str(record.search_text or "").lower()
                    score = sum(
                        1 for word in query_words
                        if word in searchable_text
                    )

                    if score > 0:
                        ranked_records.append((score, record))

                ranked_records.sort(
                    key=lambda item: item[0],
                    reverse=True
                )

                selected_records = [
                    record for score, record in ranked_records[:25]
                ]

                if selected_records:
                    knowledge_context = (
                        "UPLOADED COMPANY KNOWLEDGE BASE RECORDS:\n"
                        "Use these retrieved records as factual reference. "
                        "Do not invent missing information.\n\n"
                        + "\n".join(
                            json.dumps(
                                record.record_data,
                                ensure_ascii=False,
                                default=str
                            )
                            for record in selected_records
                        )
                    )

                    knowledge_context = knowledge_context[:24000]

                    print(
                        "KNOWLEDGE BASE RETRIEVAL:",
                        len(selected_records),
                        "records for company",
                        company.id
                    )

    finally:
        db.close()


    combined_context = context or ""

    if knowledge_context:
        combined_context += (
            "\n\n" + knowledge_context
            if combined_context else knowledge_context
        )

    return _generate_llm_response(
        customer_message=customer_message,
        intent=intent,
        context=combined_context,
        conversation_history=conversation_history,
        company_config=company_config,
        
    )
app = FastAPI(title="AI Helpdesk Bot")
@app.on_event("startup")
def initialize_knowledge_base_tables():
    Base.metadata.create_all(bind=engine)

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
    """Append the exchange, excluding temporary Zep context, and retain 20 messages."""
    history = [item for item in history if not item.get("zep_memory")]
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

    # Save the assistant response to Zep (best-effort)
    thread_uuid = state.get("zep_thread_uuid")

    if thread_uuid:
        try:
            save_assistant_turn(thread_uuid, reply)
        except Exception as exc:
            print(f"ZEP: Assistant message save failed: {exc}")

    return {"reply": reply, **payload}

def _save_and_return(state, history, user_message, reply, **payload):
    """Save the exchange and return a consistent chatbot response."""

    state["history"] = save_history(history, user_message, reply)

    # Save conversation to database
    try:
        save_conversation_exchange(
            session_id=state.get("session_id"),
            company_id=state.get("company_id"),
            customer_id=state.get("customer_id"),
            customer_email=state.get("customer_email"),
            user_message=user_message,
            bot_reply=reply,
        )
    except Exception as exc:
        print(f"CONVERSATION LOG ERROR: {exc}")

    # Save assistant response to Zep best-effort
    thread_uuid = state.get("zep_thread_uuid")
    if thread_uuid:
        try:
            save_assistant_turn(thread_uuid, reply)
        except Exception as exc:
            print(f"ZEP: Assistant message save failed: {exc}")

    return {"reply": reply, **payload}

def _save_historical_solution_feedback(
    state,
    resolution_feedback,
    feedback,
):
    """Store customer feedback about a reused historical solution."""

    matched_ticket = resolution_feedback.get("matched_ticket", {})

    db = SessionLocal()

    try:
        record = HistoricalSolutionFeedback(
            company_id=matched_ticket.get("company_id"),
            matched_ticket_id=matched_ticket.get("ticket_id"),
            customer_complaint=resolution_feedback.get("complaint", ""),
            reused_solution=matched_ticket.get("solution", ""),
            feedback=feedback,
            similarity_score=matched_ticket.get("similarity"),
            session_id=state.get("session_id"),
        )

        db.add(record)
        db.commit()

        print(f"HISTORICAL SOLUTION FEEDBACK SAVED: {feedback}")

    except Exception as exc:
        db.rollback()
        print(f"HISTORICAL FEEDBACK SAVE ERROR: {exc}")

    finally:
        db.close()


def _is_usable_approved_solution(match):
    """Reject empty, generic, or callback/handoff-only historical responses."""
    solution = str((match or {}).get("solution") or "").strip()
    if len(solution) < 30:
        return False

    normalized = re.sub(r"\s+", " ", solution.lower()).strip()
    non_actionable_phrases = (
        "please wait",
        "wait for some time",
        "wait for a while",
        "i will call you",
        "we will call you",
        "will call you",
        "call you back",
        "calling you back",
        "i'll call you",
        "we'll call you",
        "i will contact you",
        "we will contact you",
        "will contact you",
        "contact you soon",
        "our team will contact",
        "support team will contact",
        "agent will contact",
        "someone will contact",
        "connect you to an agent",
        "connect you with an agent",
        "transfer you to support",
        "escalate this issue",
        "raise a ticket",
        "create a ticket",
        "i understand the issue",
        "i understand your issue",
        "sorry for the inconvenience",
    )
    return not any(phrase in normalized for phrase in non_actionable_phrases)


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
            customer_message=(
               (pending_ticket.get("issue_summary") or "").strip()
               or pending_ticket["original_complaint"]
            ),
            
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
    state.pop("issue_messages", None)
    state.pop("human_escalation_count", None)
    state.pop("human_escalation_triggered", None)

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
    # Store conversation metadata
    state["session_id"] = session_id

    if not state.get("company_id"):
        db = SessionLocal()
        try:
            active_company = (
                db.query(Company)
                .filter(Company.is_active.is_(True))
                .first()
            )
            if active_company:
                state["company_id"] = active_company.id
        finally:
            db.close()
    # ZEP MEMORY
    customer_id = data.get("customer_id")
    state["customer_id"] = customer_id
    zep_memory_context = ""

    if customer_id:
        try:
            thread_uuid, zep_memory_context = start_user_turn(
                company_id="active_company",
                customer_id=customer_id,
                session_id=session_id,
                user_message=user_message,
            )

            if thread_uuid:
                state["zep_thread_uuid"] = thread_uuid

        except Exception as exc:
            print(f"ZEP: Memory integration failed: {exc}")

    if zep_memory_context:
        history.append({
            "role": "system",
            "content": (
                "Relevant long-term memory about this customer "
                "from previous conversations:\n"
                + zep_memory_context
            ),
            "zep_memory": True,
        })


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
    # STEP 2: HANDLE APPROVED RESOLUTION FEEDBACK
    # ------------------------------------------------

    resolution_feedback = state.get("awaiting_resolution_feedback")

    if resolution_feedback:

        choice = user_message.lower().strip()

        # --------------------------------------------
        # A. CUSTOMER CONFIRMS THE SOLUTION
        # --------------------------------------------

        if choice in {"yes", "y", "yes it did", "resolved", "it worked"}:
            _save_historical_solution_feedback(
                state,
                resolution_feedback,
                "resolved"
            )
            state.pop("awaiting_resolution_feedback", None)

            # Clear the completed issue context.
            state.pop("issue_messages", None)
            state.pop("last_customer_complaint", None)
            state.pop("last_customer_intent", None)
            state.pop("last_intervention", None)
            state.pop("last_intervention_confidence", None)

            reply = (
                "Glad I could help! Your issue has been marked as resolved. "
                "If you need anything else, feel free to ask."
            )

            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                resolution_confirmed=True,
                matched_ticket=resolution_feedback["matched_ticket"],
                response_source="agent_approved_resolution",
                conversation_status="resolution_confirmed",
            )

        # --------------------------------------------
        # B. CUSTOMER SAYS THE SOLUTION DID NOT WORK
        # --------------------------------------------

        if choice in {"no", "n", "not resolved", "did not work", "didn't work"}:

            _save_historical_solution_feedback(
                state,
                resolution_feedback,
                "not_resolved"
            )

            state.pop("awaiting_resolution_feedback", None)

            complaint = resolution_feedback["complaint"]
            intent = resolution_feedback["intent"]
            intervention = resolution_feedback["intervention"]
            intervention_confidence = resolution_feedback[
                "intervention_confidence"
            ]

            # Preserve the complete confirmed issue.
            state["pending_ticket"] = {
                "original_complaint": complaint,
                "additional_details": "",
                "detail_messages": [],
                "issue_summary": complaint,
                "intent": intent,
                "intervention": intervention,
                "intervention_confidence": intervention_confidence,
                "step": "customer_email",
                "asked_questions": [],
            }

            reply = (
                "I'm sorry that didn't work. I'll arrange further "
                "assistance from our support team.\n\n"
                "Please provide your email address so we can send "
                "you updates about your support request."
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

        # --------------------------------------------
        # C. CUSTOMER RESPONSE IS UNCLEAR
        # --------------------------------------------

        reply = (
            "Did the suggested solution resolve your issue?\n\n"
            "Please reply YES if it worked, or NO if you still need help."
        )

        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            awaiting_resolution_feedback=True,
            response_source="agent_approved_resolution",
            conversation_status="awaiting_resolution_feedback",
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
        pending_ticket.setdefault("asked_questions", [])
        pending_ticket.setdefault(
            "issue_summary",
            pending_ticket.get("original_complaint") or "",
        )

        # --------------------------------------------
        # A. Collect and interpret issue details
        # --------------------------------------------

        if current_step == "additional_details":

            # A human was requested before the customer described the issue.
            if (
                not pending_ticket.get("original_complaint")
                and not pending_ticket.get("detail_messages")
                and not pending_ticket.get("additional_details")
            ):
                domain_result = _check_company_domain(user_message, history)
                domain_decision = domain_result.get("decision", "UNCERTAIN")
                print("COMPANY DOMAIN DECISION:", domain_decision, domain_result.get("reason", ""))

                if domain_decision == "OUT_OF_DOMAIN":
                    state.pop("pending_ticket", None)
                    return _save_and_return(
                        state, history, user_message, _domain_rejection_message(),
                        ticket_created=False,
                        conversation_status="out_of_domain",
                        response_source="company_domain_validation",
                    )

                if domain_decision == "UNCERTAIN":
                    return _save_and_return(
                        state, history, user_message,
                        "I couldn't confirm that this issue relates to the company's services. "
                        "Could you explain how it connects to the company's website, "
                        "products, or services?",
                        ticket_created=False,
                        conversation_status="domain_clarification_required",
                        response_source="company_domain_validation",
                    )

                pending_ticket["original_complaint"] = user_message
                pending_ticket["issue_summary"] = user_message

            pending_conflicts = pending_ticket.get(
                "pending_contradictions", []
            )

            try:
                interpretation = interpret_ticket_message(
                    customer_message=user_message,
                    pending_ticket=pending_ticket,
                    conversation_history=history[-10:],
                    company_config=_get_active_company_config(),
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
           

            # Resolve an outstanding contradiction before normal processing.
            if pending_conflicts:
                resolution_confidence = interpretation.get(
                    "confidence", 0.0
                )

                resolved = (
                    interpretation.get("resolves_pending_contradiction")
                    is True
                    and resolution_confidence >= 0.75
                    and not interpretation.get("needs_clarification", False)
                    and not interpretation.get("contradictions", [])
                )
                corrections = interpretation.get("corrections", [])
                clarification = (
                    interpretation.get("clarification_question") or ""
                ).strip()

                if not resolved:
                    if not clarification:
                        clarification = (
                            "I still need to clarify one detail before "
                            "continuing. Could you specify which information "
                            "is correct?"
                        )

                    return _save_and_return(
                        state,
                        history,
                        user_message,
                        clarification,
                        ticket_created=False,
                        awaiting_additional_details=True,
                        conversation_status="clarifying_contradiction",
                    )

                # The customer has clarified the conflicting information.
                pending_ticket.pop("pending_contradictions", None)
                pending_ticket.pop("pending_correction", None)

                corrected_summary = (
                    interpretation.get("issue_summary") or ""
                ).strip()

                if corrected_summary:
                    pending_ticket["issue_summary"] = corrected_summary

                # Store only the corrected fact as an additional detail,
                # not the entire issue summary.
                corrected_detail = (
                    interpretation.get("relevant_details") or ""
                ).strip()

                if corrections:
                    corrected_detail = "; ".join(
                        item.strip()
                        for item in corrections
                        if isinstance(item, str) and item.strip()
                    ) or corrected_detail

                if not corrected_detail:
                    corrected_detail = user_message.strip()

                interpretation["relevant_details"] = corrected_detail

            action = interpretation.get("action", "UNCERTAIN")
            confidence = interpretation.get("confidence", 0.0)

            # Do not accept uncertain model interpretations as facts.
            if confidence < 0.65:
                action = "UNCERTAIN"


            if action == "ADD_DETAIL":
                relevant_detail = (
                    interpretation.get("relevant_details") or ""
                ).strip()

                contradictions = interpretation.get(
                    "contradictions", []
                )
                corrections = interpretation.get("corrections", [])
                missing_information = interpretation.get(
                    "missing_information", []
                )
                next_question = (
                    interpretation.get("next_question") or ""
                ).strip()

                # Clarify conflicting information before accepting it.
                if contradictions:
                    clarification = (
                        interpretation.get("clarification_question") or ""
                    ).strip()

                    if not clarification:
                        clarification = (
                            "I noticed two details that don't seem to match. "
                            "Could you clarify which information is correct?"
                        )

                    pending_ticket["pending_contradictions"] = contradictions
                    pending_ticket["pending_correction"] = relevant_detail

                    return _save_and_return(
                        state,
                        history,
                        user_message,
                        clarification,
                        ticket_created=False,
                        awaiting_additional_details=True,
                        conversation_status="clarifying_contradiction",
                    )

                if not relevant_detail:
                    action = "UNCERTAIN"
                else:
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

                    pending_ticket["missing_information"] = (
                        missing_information
                    )
                    pending_ticket["information_complete"] = (
                        interpretation.get("information_complete") is True
                    )

                                        # Prefer a new follow-up question that has not been asked before.
                    asked_questions = pending_ticket.setdefault("asked_questions", [])

                    if next_question:
                        normalized_question = " ".join(next_question.lower().split())

                        already_asked = any(
                            " ".join(str(q).lower().split()) == normalized_question
                            for q in asked_questions
                        )

                        if not already_asked:
                            reply = next_question
                            asked_questions.append(next_question)
                        else:
                            reply = (
                                "Thanks for that update. I've updated the issue details. "
                                "If you remember the error message, you can still share it. "
                                "What happened after you attempted the payment?"
                            )

                    elif pending_ticket["information_complete"]:
                        reply = (
                            "Thank you. I have the information needed "
                            "to understand your issue. You can say "
                            "'I'm done' when you're ready to review "
                            "the summary."
                        )

                    else:
                        try:
                            reply = generate_llm_response(
                                customer_message=user_message,
                                intent="customer_issue",
                                context=(
                                    "The customer is explaining an existing "
                                    "support issue.\n"
                                    f"Original complaint: "
                                    f"{pending_ticket.get('original_complaint', '')}\n"
                                    f"Additional details: "
                                    f"{pending_ticket.get('additional_details', '')}\n"
                                    f"Issue summary: "
                                    f"{pending_ticket.get('issue_summary', '')}\n"
                                    f"Missing information: "
                                    f"{missing_information}\n"
                                    f"Corrections: {corrections}\n\n"
                                    "Acknowledge the latest information "
                                    "naturally. Ask at most one useful "
                                    "follow-up question. Do not repeat "
                                    "answered questions. Do not invent facts. "
                                    "Do not mention internal AI processes."
                                ),
                                conversation_history=history,
                            )

                            reply = (reply or "").strip()
                            if not reply:
                                raise ValueError(
                                    "Gemini returned an empty response."
                                )

                        except Exception as exc:
                            print(
                                f"Conversational response generation failed: {exc}"
                            )
                            reply = (
                                "I've added that information. Is there "
                                "anything else about the issue you'd like "
                                "to share? You can say 'I'm done' when ready."
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

                # Use the complete, customer-confirmed issue summary
                complaint = (
                    pending_ticket.get("issue_summary")
                    or pending_ticket.get("original_complaint")
                    or ""
                ).strip()

                intent = pending_ticket.get("intent")
                intervention = pending_ticket.get("intervention")
                intervention_confidence = pending_ticket.get(
                    "intervention_confidence"
                )

                # Search approved resolutions only after the customer
                # confirms the complete issue summary.
                try:
                    approved_match = retrieve_approved_solution(
                        user_message=complaint,
                        intent=intent,
                    )
                except Exception as exc:
                    print(f"Approved resolution retrieval failed: {exc}")
                    approved_match = None

                

                # If a suitable solution exists, offer it naturally
                if approved_match:

                    state["awaiting_resolution_feedback"] = {
                        "complaint": complaint,
                        "intent": intent,
                        "intervention": intervention,
                        "intervention_confidence": intervention_confidence,
                        "matched_ticket": approved_match,
                    }

                    state.pop("pending_ticket", None)

                    reply = (
                        "Thanks for clarifying. You can try this:\n\n"
                        f"{approved_match['solution']}\n\n"
                        "Did this resolve the issue? Reply YES or NO."
                    )

                    return _save_and_return(
                        state,
                        history,
                        user_message,
                        reply,
                        ticket_created=False,
                        awaiting_resolution_feedback=True,
                        conversation_status="awaiting_resolution_feedback",
                    )

                # No suitable solution found — continue normal ticket process
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
        bert_start = time.perf_counter()
        first_level_result = classify_first_level_intent(user_message)
        print(f"BERT CLASSIFICATION TIME: {time.perf_counter() - bert_start:.2f}s")
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
        "human_escalation_count": state.get("human_escalation_count", 0),
    }

    # Gemini is used when BERT is uncertain.
    # It is also used for support messages to identify follow-ups,
    # explicit human requests, and the actual conversation context.
    needs_gemini_understanding = (
        first_uncertain
        or first_intent == "CUSTOMER_SUPPORT"
        or state.get("human_escalation_count", 0) > 0
        
    )

    if needs_gemini_understanding:
        try:
            gemini_start = time.perf_counter()
            turn_result = classify_conversation_turn(
                customer_message=user_message,
                conversation_history=history,
                conversation_state=conversation_context,
            )
            print(f"GEMINI CONVERSATION UNDERSTANDING TIME: {time.perf_counter() - gemini_start:.2f}s")
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
    # EARLY HUMAN-SUPPORT ESCALATION (3 EXPLICIT REQUESTS)
    # ------------------------------------------------

    if (
        category == "HUMAN_SUPPORT_REQUEST"
        and not state.get("human_escalation_triggered")
    ):
        escalation_count = state.get("human_escalation_count", 0) + 1
        state["human_escalation_count"] = escalation_count

        if escalation_count < 3:
            if escalation_count == 1:
                reply = (
                    "Of course. I'll make sure your request "
                    "for human support is taken into account."
                )
            else:
                reply = (
                    "I understand. You'd prefer to speak "
                    "with someone from our support team. "
                    "I'll make sure your request is noted."
                )

            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                human_escalation_count=escalation_count,
                conversation_status="human_escalation_requested",
            )

        # Third explicit request: prepare a ticket from available context.
        existing_pending = state.get("pending_ticket") or {}

        complaint_parts = []

        existing_complaint = (
            existing_pending.get("issue_summary")
            or existing_pending.get("original_complaint")
            or state.get("last_customer_complaint")
        )

        if existing_complaint:
            complaint_parts.append(str(existing_complaint).strip())

        issue_messages = state.get("issue_messages", [])

        if isinstance(issue_messages, list):
            for message in issue_messages:
                if message and str(message).strip():
                    complaint_parts.append(str(message).strip())

        complaint = " ".join(dict.fromkeys(complaint_parts)).strip()

        if not complaint:
            complaint = (
                "Customer repeatedly requested human support "
                "but did not provide specific issue details."
            )

        pending_ticket = {
            **existing_pending,
            "original_complaint": complaint,
            "issue_summary": complaint,
            "additional_details": existing_pending.get(
                "additional_details", ""
            ),
            "detail_messages": existing_pending.get(
                "detail_messages", []
            ),
            "asked_questions": existing_pending.get(
                "asked_questions", []
            ),
            "intent": existing_pending.get(
                "intent", "human_support_request"
            ),
            "intervention": existing_pending.get("intervention"),
            "intervention_confidence": existing_pending.get(
                "intervention_confidence", 0.0
            ),
            "step": "customer_email",
        }

        state["human_escalation_triggered"] = True
        state["pending_ticket"] = pending_ticket

        email = (
            existing_pending.get("customer_email")
            or state.get("customer_email")
        )

        if email and valid_email(email):
            pending_ticket["customer_email"] = email

            return _finish_ticket_creation(
                state,
                history,
                user_message,
                session_id,
                pending_ticket,
            )

        reply = (
            "I understand. I'll connect you with our human support team "
            "by creating a support ticket. Please provide your email "
            "address so our team can contact you."
        )

        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            human_escalation_count=escalation_count,
            awaiting_customer_email=True,
            conversation_status="awaiting_customer_email",
        )


    # ------------------------------------------------
    # STEP 5: NORMAL CHAT AND BUSINESS ENQUIRIES
    # ------------------------------------------------

    if category in {"SMALL_TALK", "GENERAL_QUESTION", "PRODUCT_ENQUIRY"}:

        response_intent = (
            "small_talk"
            if category == "SMALL_TALK" or is_small_talk(user_message)
            else (
                "business_enquiry"
                if category == "PRODUCT_ENQUIRY"
                else "general_enquiry"
            )
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

        domain_result = _check_company_domain(issue_text, history)
        domain_decision = domain_result.get("decision", "UNCERTAIN")
        print("COMPANY DOMAIN DECISION:", domain_decision, domain_result.get("reason", ""))

        if domain_decision != "IN_DOMAIN":
            state["issue_messages"] = []
            state["last_customer_complaint"] = ""

            reply = (
                _domain_rejection_message()
                if domain_decision == "OUT_OF_DOMAIN"
                else "I couldn't confirm that this issue relates to the company's services. "
                     "Could you explain how it is connected to the company's website, "
                     "products, or services?"
            )
            return _save_and_return(
                state, history, user_message, reply,
                ticket_created=False,
                conversation_status="out_of_domain" if domain_decision == "OUT_OF_DOMAIN"
                else "domain_clarification_required",
                response_source="company_domain_validation",
            )

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

        domain_result = _check_company_domain(issue_text, history)
        domain_decision = domain_result.get("decision", "UNCERTAIN")
        print("COMPANY DOMAIN DECISION:", domain_decision, domain_result.get("reason", ""))

        if domain_decision != "IN_DOMAIN":
            state["last_customer_complaint"] = ""
            state["issue_messages"] = []
            state.pop("pending_ticket", None)

            reply = (
                _domain_rejection_message()
                if domain_decision == "OUT_OF_DOMAIN"
                else "I couldn't confirm that this issue relates to the company's services. "
                     "Please explain how it connects to the company's website, products, "
                     "or services before I can continue."
            )
            return _save_and_return(
                state, history, user_message, reply,
                ticket_created=False,
                conversation_status="out_of_domain" if domain_decision == "OUT_OF_DOMAIN"
                else "domain_clarification_required",
                response_source="company_domain_validation",
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

        original_complaint = (
            original_complaint or ""
        ).strip()

        pending_ticket = {
            "original_complaint": original_complaint,
            "additional_details": "",
            "detail_messages": [],
            "issue_summary": original_complaint,
            "intent": intent,
            "intervention": intervention,
            "intervention_confidence": intervention_confidence,
            "step": "additional_details",
            "asked_questions": [],
        }

        try:
            interpretation = interpret_ticket_message(
                customer_message=original_complaint or user_message,
                pending_ticket=pending_ticket,
                conversation_history=history[-10:],
                company_config=_get_active_company_config(),
            )

            issue_summary = (
                interpretation.get("issue_summary") or original_complaint
            ).strip()

            missing_information = interpretation.get(
                "missing_information", []
            )

            information_complete = (
                interpretation.get("information_complete") is True
            )

            next_question = (
                interpretation.get("next_question") or ""
            ).strip()

            clarification = (
                interpretation.get("clarification_question") or ""
            ).strip()

            pending_ticket["issue_summary"] = issue_summary
            pending_ticket["missing_information"] = missing_information
            pending_ticket["information_complete"] = information_complete

            state["pending_ticket"] = pending_ticket

            if clarification:
                reply = clarification

            elif next_question and not information_complete:
                reply = next_question
                pending_ticket["asked_questions"].append(next_question)

            else:
                reply = generate_llm_response(
                    customer_message=original_complaint or user_message,
                    intent="customer_issue",
                    context=(
                        "The customer has requested human support.\n"
                        f"Complaint: {original_complaint}\n"
                        f"Issue summary: {issue_summary}\n"
                        f"Missing information: {missing_information}\n"
                        f"Information complete: {information_complete}\n\n"
                        "Respond naturally to the customer based on the "
                        "actual complaint and the analysis above. If "
                        "information is already sufficient, explain the "
                        "next step naturally. If information is missing, "
                        "ask one relevant question. Do not assume a "
                        "specific business domain or request generic "
                        "identifiers. Do not invent facts."
                    ),
                    conversation_history=history,
                )

                reply = (reply or "").strip()

                if not reply:
                    raise ValueError("Gemini returned an empty response.")

        except Exception as exc:
            print(f"Initial ticket analysis failed: {exc}")
            raise HTTPException(
                status_code=503,
                detail=(
                    "Unable to analyse your support request. "
                    "Please try again."
                ),
            )

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
    print("===== FINAL ISSUE CLASSIFICATION =====")
    print("ISSUE TEXT:", issue_text)
    print("INTENT:", intent)
    print("INTERVENTION:", intervention)
    print("INTERVENTION CONFIDENCE:", intervention_confidence)
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
    # B. FALL BACK TO EXISTING LEGACY JSON RETRIEVAL
    # --------------------------------------------

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

    state["history"] = save_history(
        history,
        user_message,
        support_reply
    )

    # Save the assistant response to Zep for this conversation (best-effort).
    thread_uuid = state.get("zep_thread_uuid")
    if thread_uuid:
        try:
            save_assistant_turn(thread_uuid, support_reply)
        except Exception as exc:
            print(f"ZEP: Assistant message save failed: {exc}")

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
app.include_router(knowledge_base_router)
app.include_router(conversation_router)
"""Application entry point for the AI Helpdesk backend."""

import re
import time
import json

from urllib import response
import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from services.zep_memory_service import save_assistant_turn, start_user_turn
from services.first_level_intent_service import classify_first_level_intent
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
from routes.historical_solution_routes import router as historical_solution_router
from routes.historical_attempt_routes import router as historical_attempt_router
from routes.internal_admin_routes import router as internal_admin_router
from database.database import SessionLocal
from database.models import (
    Ticket,
    Company,
    BotConfiguration,
    Conversation,
    ConversationMessage,
    HistoricalSolutionFeedback,
    HistoricalSolutionAttempt,
    PendingTicketConversation,
    TicketConversationSettings,
    TicketIntakeConfiguration,
)

def _get_active_company_config(company_id=None):
    """Load the correct active company's saved bot instructions."""
    db = SessionLocal()
    try:
        q = db.query(Company).filter(Company.is_active.is_(True))
        if company_id is not None:
            q = q.filter(Company.id == company_id)
        company = q.first()
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


def _check_company_domain(issue_text, conversation_history=None, company_id=None):
    config = _get_active_company_config(company_id)
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
    conversation_history: list = None,
    company_id=None
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
        q = db.query(Company).filter(Company.is_active.is_(True))
        if company_id is not None:
            q = q.filter(Company.id == company_id)
        company = q.first()

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
            if product_catalogue_records and intent == "business_enquiry":
                available_product_groups = sorted({
                    str(record.record_data.get("Group", "")).upper()
                    for record in product_catalogue_records
                    if record.record_data.get("Group")
                })

                # Let Gemini understand the request and plan retrieval.
                try:
                    planner_start = time.perf_counter()

                    retrieval_plan = plan_knowledge_retrieval(
                        customer_message=customer_message,
                        available_product_groups=available_product_groups,
                        conversation_history=conversation_history
                    )
                    print(
                         f"GEMINI PRODUCT PLANNER TIME: "
                         f"{time.perf_counter() - planner_start:.2f}s"
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

    generation_start = time.perf_counter()

    response = _generate_llm_response(
        customer_message=customer_message,
        intent=intent,
        context=combined_context,
        conversation_history=conversation_history,
        company_config=company_config,
    )

    print(
        f"GEMINI FINAL RESPONSE TIME: "
        f"{time.perf_counter() - generation_start:.2f}s"
    )

    print(
        f"TOTAL RESPONSE WRAPPER TIME: "
        f"{time.perf_counter() - start_time:.2f}s"
    )

    return response
    



app = FastAPI(title="AI Helpdesk Bot")
async def historical_solution_timeout_checker():
    print("Historical solution timeout checker started.")

    while True:
        db = SessionLocal()

        try:
            pending_attempts = (
                db.query(HistoricalSolutionAttempt, Company)
                .join(
                    Company,
                    HistoricalSolutionAttempt.company_id == Company.id,
                )
                .filter(
                    HistoricalSolutionAttempt.attempt_status == "pending",
                    Company.historical_solution_timeout_enabled.is_(True),
                )
                .all()
            )

            now = datetime.now(timezone.utc)

            for attempt, company in pending_attempts:
                created_at = attempt.created_at

                if created_at is None:
                    continue

                if created_at.tzinfo is None:
                    created_at = created_at.replace(
                        tzinfo=timezone.utc
                    )

                elapsed_hours = (
                    now - created_at
                ).total_seconds() / 3600

                timeout_hours = (
                    company.historical_solution_timeout_hours
                )

                if elapsed_hours >= timeout_hours:
                    attempt.attempt_status = "abandoned"

                    print(
                        f"Attempt {attempt.id} marked abandoned "
                        f"after {elapsed_hours:.2f} hours."
                    )

            db.commit()

        except Exception as e:
            db.rollback()
            print(
                f"Historical timeout checker error: {e}"
            )

        finally:
            db.close()

        await asyncio.sleep(60)


async def ticket_conversation_timeout_checker():
    """Submit incomplete ticket workflows after company-configured inactivity."""
    print("Ticket conversation inactivity checker started.")
    while True:
        db = SessionLocal()
        try:
            active_rows = db.query(PendingTicketConversation).filter(
                PendingTicketConversation.status == "active"
            ).all()
            now = datetime.now(timezone.utc)
            for row in active_rows:
                settings = db.query(TicketConversationSettings).filter(
                    TicketConversationSettings.company_id == row.company_id
                ).first()
                enabled = settings.enabled if settings else True
                timeout_minutes = settings.timeout_minutes if settings else 2
                if not enabled:
                    continue
                last_activity = row.last_activity
                if last_activity is None:
                    continue
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
                if (now - last_activity).total_seconds() < timeout_minutes * 60:
                    continue

                state = row.state_data if isinstance(row.state_data, dict) else {}
                pending = state.get("pending_ticket") or {}
                email = pending.get("customer_email") or state.get("customer_email")
                if not pending:
                    db.delete(row)
                    db.commit()
                    continue
                if email and valid_email(email):
                    pending["customer_email"] = email
                if _next_missing_ticket_field(pending, row.company_id):
                    row.status = "awaiting_confirmation"
                    db.commit()
                    continue

                # Recover safely if a process stopped after creating this
                # exact ticket but before removing its pending conversation.
                existing_ticket = db.query(Ticket).filter(
                    Ticket.session_id == row.session_id,
                    Ticket.company_id == row.company_id,
                    Ticket.chatbot_id == row.chatbot_id,
                    Ticket.customer_email == email,
                    Ticket.customer_message == (pending.get("original_complaint") or ""),
                ).first()
                if existing_ticket:
                    db.delete(row)
                    db.commit()
                    continue

                state["session_id"] = row.session_id
                state["company_id"] = row.company_id
                state["chatbot_id"] = row.chatbot_id
                state["_timeout_submission"] = True
                history = state.setdefault("history", [])
                try:
                    result = _finish_ticket_creation(
                        state,
                        history,
                        "The customer did not respond before the ticket conversation timed out.",
                        row.session_id,
                        pending,
                    )
                    state_key = (
                        f"{state.get('bot_public_id')}:{row.session_id}"
                        if state.get("bot_public_id")
                        else row.session_id
                    )
                    conversation_states[state_key] = state
                    print(
                        "TICKET CONVERSATION TIMEOUT:",
                        row.session_id,
                        result.get("ticket_id"),
                        result.get("conversation_status"),
                    )
                except Exception as exc:
                    print(f"TICKET CONVERSATION TIMEOUT SUBMISSION ERROR: {exc}")
                    row.status = "active"
                    row.last_activity = now
                    db.commit()
        except Exception as exc:
            db.rollback()
            print(f"Ticket conversation timeout checker error: {exc}")
        finally:
            db.close()
        await asyncio.sleep(10)


@app.on_event("startup")
async def initialize_knowledge_base_tables():
    Base.metadata.create_all(bind=engine)

    asyncio.create_task(
        historical_solution_timeout_checker()
    )
    asyncio.create_task(
        ticket_conversation_timeout_checker()
    )

# In-memory cache is only an optimization. Active ticket-raising state is
# also persisted in PostgreSQL so browser reloads and backend restarts are safe.
conversation_states = {}


def _persist_pending_ticket_state(state):
    """Persist only active ticket-raising workflows; never FAQ/general chat."""
    session_id = state.get("session_id")
    company_id = state.get("company_id")
    chatbot_id = state.get("chatbot_id")
    pending_ticket = state.get("pending_ticket")
    db = SessionLocal()
    try:
        row = db.query(PendingTicketConversation).filter(
            PendingTicketConversation.company_id == company_id,
            PendingTicketConversation.chatbot_id == chatbot_id,
            PendingTicketConversation.session_id == session_id,
        ).first()
        if not pending_ticket:
            if row:
                db.delete(row)
                db.commit()
            return
        snapshot = json.loads(json.dumps(state, ensure_ascii=False, default=str))
        status = "awaiting_confirmation" if state.get("duplicate_confirmation") else "active"
        if not row:
            row = PendingTicketConversation(
                company_id=company_id,
                chatbot_id=chatbot_id,
                session_id=session_id,
                customer_id=state.get("customer_id"),
                customer_email=pending_ticket.get("customer_email") or state.get("customer_email"),
                state_data=snapshot,
                status=status,
            )
            db.add(row)
        else:
            row.customer_id = state.get("customer_id")
            row.customer_email = pending_ticket.get("customer_email") or state.get("customer_email")
            row.state_data = snapshot
            row.status = status
            row.last_activity = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"PENDING TICKET STATE PERSIST ERROR: {exc}")
    finally:
        db.close()


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
        "http://localhost:5175",
        "http://127.0.0.1:5175",
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


def is_explicit_immediate_ticket_request(message):
    """Recognize a clear instruction to submit the pending support request now."""
    normalized = re.sub(r"[^a-z0-9' ]+", " ", str(message).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    patterns = (
        r"\b(?:raise|create|submit|open|log)\s+(?:a\s+)?ticket\b",
        r"\b(ticket|support request)\s+(?:now|immediately)\b",
        r"\braise\s+(?:it|this|the request)\s+now\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def is_ticket_cancellation(message):
    """Return True only when the customer explicitly withdraws the support request."""
    normalized = re.sub(r"[^a-z0-9' ]+", " ", str(message).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = normalized.replace("don't", "do not")
    normalized = normalized.replace("doesn't", "does not")
    normalized = normalized.replace("didn't", "did not")

    # A bare "cancel" is deliberately excluded here. It is accepted only
    # in workflow states where the bot has explicitly offered CANCEL.
    explicit_patterns = (
        r"^(?:please )?(?:cancel|stop|withdraw|close) (?:the |my |this )?(?:(?:human )?support )?(?:ticket|request)$",
        r"^(?:i do not want|i do not need|i no longer want|i no longer need) (?:a |the )?(?:(?:human )?support )?(?:ticket|request)$",
        r"^(?:i do not want|i do not need|i no longer want|i no longer need) (?:a |the )?(?:human )?agent$",
        r"^(?:i do not want|i do not need|i no longer want|i no longer need) (?:human )?support$",
        r"^no (?:(?:human )?support )?(?:ticket|request) needed$",
        r"^no (?:human )?agent needed$",
        r"^(?:please )?do not (?:create|raise) (?:a |the )?(?:(?:human )?support )?(?:ticket|request)$",
        r"^(?:never mind|nevermind) (?:the )?(?:(?:human )?support )?(?:ticket|request)$",
    )
    return any(re.fullmatch(pattern, normalized) for pattern in explicit_patterns)


def is_urgent_safety_message(message):
    """Detect clear physical danger or robbery/theft situations."""
    normalized = re.sub(r"[^a-z0-9 ]+", " ", message.lower())
    normalized = " ".join(normalized.split())

    direct_danger_terms = (
        "robbed", "robbery", "mugged", "mugging",
        "snatched", "snatching", "attacked", "assaulted",
        "kidnapped", "threatened",
    )

    financial_context_terms = (
        "atm", "cash", "money", "withdrawal",
        "wallet", "purse", "bank", "rupees",
    )

    has_direct_danger = any(
        term in normalized for term in direct_danger_terms
    )
    has_financial_context = any(
        term in normalized for term in financial_context_terms
    )

    describes_cash_robbery = (
        has_financial_context
        and any(term in normalized for term in (
            "pulled the money",
            "took the money",
            "grabbed the money",
            "escaped with",
            "ran away with",
            "stole the cash",
            "stole my money",
        ))
    )

    return (
        (has_direct_danger and has_financial_context)
        or describes_cash_robbery
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

def get_ticket_category(intent):
    intent = (intent or "").lower().strip()

    category_mapping = {
        "login_issue": "Login / Authentication",
        "authentication": "Login / Authentication",
        "delivery_tracking": "Delivery / Shipping",
        "delivery_issue": "Delivery / Shipping",
        "duplicate_payment": "Payment / Billing",
        "payment_issue": "Payment / Billing",
        "refund_request": "Refunds / Returns",
        "return_request": "Refunds / Returns",
        "technical_issue": "Technical Issues",
        "bug_report": "Technical Issues",
        "account_issue": "Account Management",
        "account_management": "Account Management",
        "product_question": "Product / Service Questions",
        "feature_request": "Feature Requests",
    }

    return category_mapping.get(intent, "Other")

def create_support_ticket(
    customer_message,
    additional_details,
    customer_email,
    intent,
    session_id,
    company_id=None,
    chatbot_id=None,
    custom_fields=None,
):
    
    """Create a ticket in the configured database."""
    db = SessionLocal()
    try:
        ticket = Ticket(
            company_id=company_id,
            chatbot_id=chatbot_id,
            ticket_id=f"TKT-{uuid.uuid4().hex[:8].upper()}",
            session_id=session_id,
            customer_message=customer_message,
            additional_details=additional_details,
            customer_email=customer_email,
            custom_fields=custom_fields or {},
            intent=intent,
            category=get_ticket_category(intent),
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
        "connect me",
        "just connect me",
        "connect me to the human",
        "connect me to a human agent",
        "i need to speak to the human",
        "i need to speak to a human",
        "i need to talk to the human",
        "i need to talk to a human",
        "speak to the human",
        "talk to the human",
        "just connect me to the human",
        "just connect me to a human",
        "connect me with a human",
        "connect me with the human agent",
        "i want a human",
        "i want to speak to support",
        "i want to talk to support",
        "please connect me",
    ]
    return any(phrase in message for phrase in request_phrases)


def _save_and_return(state, history, user_message, reply, **payload):
    """Save chat history and persist only successfully created ticket conversations."""

    state["history"] = save_history(history, user_message, reply)

    ticket_buffer = state.get("ticket_conversation_buffer", [])

    if state.get("pending_ticket"):
        if state.pop("_timeout_submission", False):
            ticket_buffer.append({
                "user_message": "",
                "bot_reply": reply,
            })
        else:
            ticket_buffer.append({
                "user_message": user_message,
                "bot_reply": reply,
            })
        state["ticket_conversation_buffer"] = ticket_buffer

    elif payload.get("ticket_created") is True:
        if state.pop("_timeout_submission", False):
            ticket_buffer.append({
                "user_message": "",
                "bot_reply": reply,
            })
        else:
            ticket_buffer.append({
                "user_message": user_message,
                "bot_reply": reply,
            })

        try:
            for exchange in ticket_buffer:
                save_conversation_exchange(
                    session_id=state.get("session_id"),
                    company_id=state.get("company_id"),
                    chatbot_id=state.get("chatbot_id"),
                    customer_id=state.get("customer_id"),
                    customer_email=state.get("customer_email"),
                    user_message=exchange["user_message"],
                    bot_reply=exchange["bot_reply"],
                )
        except Exception as exc:
            print(f"CONVERSATION LOG ERROR: {exc}")
        finally:
            state.pop("ticket_conversation_buffer", None)

    else:
        state.pop("ticket_conversation_buffer", None)

    _persist_pending_ticket_state(state)

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
def _create_historical_solution_attempt(
    state,
    complaint,
    matched_ticket,
    response_delivered,
):
    """Create a database record for a historical solution attempt."""

    db = SessionLocal()

    try:
        company_id = (
            matched_ticket.get("company_id")
            or state.get("company_id")
        )

        chatbot_id = state.get("chatbot_id")

        if not company_id or not chatbot_id:
            print(
                "HISTORICAL ATTEMPT ERROR: "
                "Company ID or Chatbot ID missing."
            )
            return None

        record = HistoricalSolutionAttempt(
            company_id=company_id,
            chatbot_id=chatbot_id,
            session_id=state.get("session_id"),
            customer_email=state.get("customer_email"),
            customer_complaint=complaint,
            matched_ticket_id=matched_ticket.get("ticket_id"),
            retrieved_solution=matched_ticket.get("solution"),
            similarity_score=matched_ticket.get("similarity"),
            response_delivered=response_delivered,
            resolution_confirmation="pending",
            attempt_status="pending",
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        print(
            "HISTORICAL ATTEMPT CREATED:",
            f"id={record.id},",
            f"company={record.company_id},",
            f"chatbot={record.chatbot_id}",
        )

        return record.id

    except Exception as exc:
        db.rollback()
        print(f"HISTORICAL ATTEMPT SAVE ERROR: {exc}")
        return None

    finally:
        db.close()

def _update_historical_solution_attempt(
    attempt_id,
    chatbot_id,
    resolution_confirmation=None,
    attempt_status=None,
    created_ticket_id=None,
):
    """Update a historical solution attempt belonging to a chatbot."""

    if not attempt_id or not chatbot_id:
        return

    db = SessionLocal()

    try:
        record = (
            db.query(HistoricalSolutionAttempt)
            .filter(
                HistoricalSolutionAttempt.id == attempt_id,
                HistoricalSolutionAttempt.chatbot_id == chatbot_id,
            )
            .first()
        )

        if not record:
            print(
                "HISTORICAL ATTEMPT UPDATE: "
                f"Record {attempt_id} not found for chatbot {chatbot_id}."
            )
            return

        if resolution_confirmation is not None:
            record.resolution_confirmation = resolution_confirmation

        if attempt_status is not None:
            record.attempt_status = attempt_status

        if created_ticket_id is not None:
            record.created_ticket_id = created_ticket_id

        db.commit()

        print(
            f"HISTORICAL ATTEMPT UPDATED: "
            f"{attempt_id}, chatbot={chatbot_id}"
        )

    except Exception as exc:
        db.rollback()
        print(f"HISTORICAL ATTEMPT UPDATE ERROR: {exc}")

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


def _first_investigation_question(complaint):
    """Ask an open, issue-specific question without assuming the cause."""
    text = (complaint or "").lower()

    if re.search(r"\b(payment|paid|charge|charged|debit|debited|transaction|billing)\b", text):
        return "Could you briefly explain what happened with your payment?"
    if re.search(r"\b(delivery|shipping|shipment|order|package)\b", text):
        return "Could you briefly explain what happened with your order or delivery?"
    if re.search(r"\b(login|log in|sign in|signin|account|password)\b", text):
        return "What happens when you try to sign in to your account?"
    if re.search(r"\b(refund|reimburse|money back)\b", text):
        return "Could you tell me what happened with your refund?"
    if re.search(r"\b(product|device|item|goods)\b", text):
        return "Could you briefly explain what problem you're experiencing with the product?"

    return "Could you briefly explain what happened?"


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
    existing_pending = state.get("pending_ticket") or {}
    collected_email = (
        existing_pending.get("customer_email")
        or state.get("customer_email")
    )
    state["pending_ticket"] = {
        "customer_email": collected_email,
        "original_complaint": complaint,
        "additional_details": "",
        "detail_messages": [],
        "issue_summary": complaint or "",
        "intent": intent,
        "intervention": intervention,
        "intervention_confidence": intervention_confidence,
        "human_support_requested": bool(existing_pending.get("human_support_requested")),
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



def _check_duplicate_ticket(
    pending_ticket,
    email,
    company_id=None,
    chatbot_id=None,
):
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
            company_id=company_id,
            chatbot_id=chatbot_id,
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

    custom_fields = pending_ticket.get("custom_fields") or {}
    if custom_fields:
        sections.append(
            "Configured customer information:\n" +
            "\n".join(f"{key}: {value}" for key, value in custom_fields.items())
        )

    return "\n\n".join(sections)


def _get_ticket_intake_fields(company_id, intent):
    db = SessionLocal()
    try:
        row = db.query(TicketIntakeConfiguration).filter(TicketIntakeConfiguration.company_id == company_id).first()
        if not row:
            return [{"key": "email", "label": "Email address", "type": "email", "required": True, "prompt": "What email address should our support team use to send you updates?"}]
        config = row.configuration if isinstance(row.configuration, dict) else {}
        fields = list(config.get("global_fields") or [])
        category_name = get_ticket_category(intent or "").strip().lower()
        intent_key = re.sub(r"[^a-z0-9]+", "_", str(intent or "").lower()).strip("_")
        for category in config.get("categories") or []:
            key = str(category.get("key") or "").lower()
            label = re.sub(r"[^a-z0-9]+", " ", str(category.get("label") or "").lower()).strip()
            normalized_category = re.sub(r"[^a-z0-9]+", " ", category_name).strip()
            if key == intent_key or (label and label == normalized_category):
                fields.extend(category.get("fields") or [])
                break
        return fields
    finally:
        db.close()


def _ticket_email_required(company_id, intent):
    return any(
        (field.get("key") == "email" or field.get("type") == "email") and field.get("required", False)
        for field in _get_ticket_intake_fields(company_id, intent)
    )


def _next_missing_ticket_field(pending_ticket, company_id):
    values = pending_ticket.setdefault("custom_fields", {})
    for field in _get_ticket_intake_fields(company_id, pending_ticket.get("intent")):
        if not field.get("required", False):
            continue
        key = field.get("key")
        value = pending_ticket.get("customer_email") if (key == "email" or field.get("type") == "email") else values.get(key)
        if value is None or not str(value).strip():
            return field
    return None


def _ask_for_ticket_field(state, history, user_message, pending_ticket, field):
    pending_ticket["step"] = "collecting_custom_fields"
    pending_ticket["current_intake_field"] = field.get("key")
    question = (field.get("prompt") or "").strip() or f"Could you provide your {field.get('label', 'requested information')}?"
    return _save_and_return(state, history, user_message, question, ticket_created=False, awaiting_custom_field=True, required_field=field.get("key"), conversation_status="collecting_ticket_information")


def _finish_ticket_creation(state, history, user_message, session_id, pending_ticket):
    """Check for duplicates and create the ticket when appropriate."""
    email = pending_ticket.get("customer_email")
    missing_field = _next_missing_ticket_field(pending_ticket, state.get("company_id"))
    if missing_field:
        return _ask_for_ticket_field(state, history, user_message, pending_ticket, missing_field)

    if (
        email
        and not pending_ticket.get("force_new_ticket")
        and not pending_ticket.get("skip_duplicate_check")
    ):
        try:
            duplicate = _check_duplicate_ticket(
                pending_ticket,
                email,
                company_id=state.get("company_id"),
                chatbot_id=state.get("chatbot_id"),
            )
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
            custom_fields=pending_ticket.get("custom_fields") or {},
            intent=pending_ticket["intent"],
            session_id=session_id,
            company_id=state.get("company_id"),
            chatbot_id=state.get("chatbot_id"),
        )
    except Exception as exc:
        print(f"Ticket creation failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to create your ticket. Please try again.",
        )

    # Link the failed historical solution attempt to the new ticket.
    _update_historical_solution_attempt(
        attempt_id=pending_ticket.get("historical_attempt_id"),
        chatbot_id=pending_ticket.get("chatbot_id"),
        resolution_confirmation="no",
        attempt_status="ticket_created",
        created_ticket_id=ticket_id,
    )

    intervention = pending_ticket["intervention"]
    intervention_confidence = pending_ticket["intervention_confidence"]

    queued_issue = state.pop("queued_separate_issue", None)

    state.pop("pending_ticket", None)
    state.pop("duplicate_confirmation", None)
    state.pop("issue_messages", None)
    state.pop("last_customer_complaint", None)
    state.pop("last_customer_intent", None)
    state.pop("last_intervention", None)
    state.pop("last_intervention_confidence", None)
    state.pop("human_escalation_count", None)
    state.pop("human_escalation_triggered", None)
    state.pop("human_support_issue_pending", None)

    if queued_issue:
        next_pending = dict(pending_ticket)
        next_pending["original_complaint"] = queued_issue
        next_pending["issue_summary"] = queued_issue
        next_pending["additional_details"] = ""
        next_pending["detail_messages"] = [queued_issue]
        next_pending["asked_questions"] = []
        next_pending["step"] = "additional_details"
        next_pending["historical_attempt_id"] = None
        next_pending.pop("new_issue_candidate", None)
        state["pending_ticket"] = next_pending

        reply = (
            "Your first support ticket has been created successfully.\n\n"
            f"Ticket ID: {ticket_id}\n"
            f"Registered email: {email}\n\n"
            "Now let's work on your separate issue. Please share any details "
            "that will help our support team."
        )
        conversation_status = "ticket_created_next_issue_pending"
    else:
        reply = (
            "Thank you! Your support ticket has been successfully created.\n\n"
            f"Ticket ID: {ticket_id}\n"
            f"Registered email: {email}\n\n"
            "Our human support team will review your complaint "
            "and send updates to your email address."
        )
        conversation_status = "ticket_created"

    return _save_and_return(
        state,
        history,
        user_message,
        reply,
        ticket_created=True,
        ticket_id=ticket_id,
        intervention=intervention,
        intervention_confidence=intervention_confidence,
        conversation_status=conversation_status,
        response_source="automatic_ticket_creation",
    )


# ------------------------------------------------
# CHAT ENDPOINT
# ------------------------------------------------

@app.get("/chat/resume")
def resume_ticket_conversation(session_id: str, bot_public_id: str):
    """Return only a still-pending ticket conversation for widget restoration."""
    db = SessionLocal()
    try:
        from database.models import Chatbot
        chatbot = db.query(Chatbot).filter(
            Chatbot.public_id == bot_public_id,
            Chatbot.status == "active",
        ).first()
        if not chatbot:
            return {"messages": []}
        pending = db.query(PendingTicketConversation).filter(
            PendingTicketConversation.company_id == chatbot.organization_id,
            PendingTicketConversation.chatbot_id == chatbot.id,
            PendingTicketConversation.session_id == session_id,
            PendingTicketConversation.status.in_(["active", "awaiting_confirmation"]),
        ).first()
        if pending and isinstance(pending.state_data, dict):
            history = pending.state_data.get("history") or []
            messages = [
                {
                    "sender": "user" if item.get("role") == "user" else "bot",
                    "text": item.get("content", ""),
                }
                for item in history
                if item.get("role") in {"user", "assistant"} and item.get("content")
            ]
            return {"messages": messages}

        # If inactivity already submitted the ticket, restore the saved
        # ticket-raising transcript including the generated ticket number.
        conversation = db.query(Conversation).filter(
            Conversation.company_id == chatbot.organization_id,
            Conversation.chatbot_id == chatbot.id,
            Conversation.session_id == session_id,
        ).order_by(Conversation.last_activity.desc()).first()
        if not conversation:
            return {"messages": []}
        saved_messages = db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conversation.id
        ).order_by(ConversationMessage.timestamp.asc()).all()
        return {
            "messages": [
                {
                    "sender": "user" if item.sender == "customer" else "bot",
                    "text": item.content,
                }
                for item in saved_messages
            ]
        }
    finally:
        db.close()


@app.post("/chat")
def chat(data: dict):
    user_message = data.get("message", "")
    session_id = data.get("session_id", "demo-session")
    bot_public_id = data.get("bot_public_id")

    if not isinstance(user_message, str) or not user_message.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid customer message.",
        )

    user_message = user_message.strip()

    # Resolve chatbot identity and its organization
    db = SessionLocal()
    try:
        if bot_public_id:
            from database.models import Chatbot

            chatbot = db.query(Chatbot).filter(
                Chatbot.public_id == bot_public_id,
                Chatbot.status == "active",
            ).first()

            if not chatbot:
                raise HTTPException(
                    status_code=404,
                    detail="Chatbot not found or inactive.",
                )

            company = db.query(Company).filter(
                Company.id == chatbot.organization_id,
                Company.is_active.is_(True),
            ).first()

            if not company:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found or inactive.",
                )

            company_id = company.id
            chatbot_id = chatbot.id

        else:
            raise HTTPException(
                status_code=400,
                detail="Chatbot ID is required.",
            )



    finally:
        db.close()

    # Separate conversation states between chatbots
    state_key = (
        f"{bot_public_id}:{session_id}"
        if bot_public_id
        else session_id
    )

    # Reset inactivity as soon as a customer message reaches the backend,
    # before semantic/LLM processing begins.
    activity_db = SessionLocal()
    try:
        activity_row = activity_db.query(PendingTicketConversation).filter(
            PendingTicketConversation.company_id == company_id,
            PendingTicketConversation.chatbot_id == chatbot_id,
            PendingTicketConversation.session_id == session_id,
            PendingTicketConversation.status.in_(["active", "awaiting_confirmation"]),
        ).first()
        if activity_row:
            activity_row.last_activity = datetime.now(timezone.utc)
            activity_row.status = "active"
            activity_db.commit()
    finally:
        activity_db.close()

    state = conversation_states.setdefault(state_key, {})
    # Restore the in-progress ticket workflow from PostgreSQL. This also
    # restores its transcript when the customer reloads the widget.
    restore_db = SessionLocal()
    try:
        saved = restore_db.query(PendingTicketConversation).filter(
            PendingTicketConversation.company_id == company_id,
            PendingTicketConversation.chatbot_id == chatbot_id,
            PendingTicketConversation.session_id == session_id,
            PendingTicketConversation.status.in_(["active", "awaiting_confirmation"]),
        ).first()
        if saved and isinstance(saved.state_data, dict):
            state.update(saved.state_data)
    finally:
        restore_db.close()
    print("CHAT STATE TRACE:", state_key, "pending:", (state.get("pending_ticket") or {}).get("step"), "state_id:", id(state))
    history = state.setdefault("history", [])

    state["session_id"] = session_id
    state["company_id"] = company_id
    state["chatbot_id"] = chatbot_id
    state["bot_public_id"] = bot_public_id

    user_message = user_message.strip()

    # Store conversation metadata in the chatbot-specific state
    state["session_id"] = session_id
    state["company_id"] = company_id
    state["chatbot_id"] = chatbot_id
    state["bot_public_id"] = bot_public_id


    # ZEP MEMORY
    customer_id = data.get("customer_id")
    state["customer_id"] = customer_id
    zep_memory_context = ""

    if customer_id:
        zep_start_time = time.perf_counter()

        try:
            thread_uuid, zep_memory_context = start_user_turn(
                company_id=company_id,
                customer_id=customer_id,
                session_id=session_id,
                user_message=user_message,
            )

            if thread_uuid:
                state["zep_thread_uuid"] = thread_uuid

        except Exception as exc:
            print(f"ZEP: Memory integration failed: {exc}")

        finally:
            print(
                f"ZEP TOTAL TIME: "
                f"{time.perf_counter() - zep_start_time:.2f}s"
            )

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


    # Understand the message semantically before ticket and domain routing.
    conversation_context = {
        "last_customer_complaint": state.get("last_customer_complaint", ""),
        "issue_messages": state.get("issue_messages", []),
        "human_escalation_count": state.get("human_escalation_count", 0),
        "human_support_issue_pending": bool(state.get("human_support_issue_pending")),
        "pending_ticket_exists": bool(state.get("pending_ticket")),
        "pending_ticket_step": (state.get("pending_ticket") or {}).get("step", ""),
    }

    turn_result = None
    try:
        gemini_start = time.perf_counter()
        turn_result = classify_conversation_turn(
            customer_message=user_message,
            conversation_history=history,
            conversation_state=conversation_context,
        )
        print(
            "GEMINI CONVERSATION UNDERSTANDING TIME:",
            f"{time.perf_counter() - gemini_start:.2f}s",
        )
    except Exception as exc:
        # Keep normal chat available if the early semantic call fails.
        print(f"Early conversation understanding failed: {exc}")

    semantic_category = str(
        (turn_result or {}).get("category", "UNCERTAIN")
    ).upper()

    semantic_human_request = semantic_category == "HUMAN_SUPPORT_REQUEST"

    if turn_result and turn_result.get("safety_concern") is True:
        print("SEMANTIC SAFETY TYPE:", turn_result.get("safety_type", ""))

        reply = (
            "I'm sorry you're dealing with this. Your safety comes first. "
            "If you are in immediate danger, move to a safe place and call "
            "your local emergency number. If you are in India, call 112.\n\n"
            "Please report the incident to the local police as appropriate. "
            "Do not confront anyone who may have harmed or threatened you. "
            "Keep relevant evidence and details that may help authorities.\n\n"
            "If a bank account, card, ATM withdrawal, or unauthorized "
            "transaction is involved, contact your bank immediately. In India, "
            "1930 is for unauthorized digital financial transactions, not "
            "physical theft alone.\n\n"
            "I cannot contact the police or your bank on your behalf."
        )

        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            conversation_status="urgent_safety_guidance",
            response_source="semantic_safety_classification",
        )

    # Only an explicit withdrawal of the support request may cancel it.
    # Semantic classification alone must never discard an active complaint:
    # cancelled orders, shipments, payments, and bookings are issue details.
    support_request_pending = bool(
        state.get("pending_ticket")
        or state.get("human_support_issue_pending")
        or state.get("human_escalation_count")
    )

    if support_request_pending and is_ticket_cancellation(user_message):
        state.pop("pending_ticket", None)
        state.pop("duplicate_confirmation", None)
        state.pop("human_escalation_count", None)
        state.pop("human_escalation_triggered", None)
        state.pop("human_support_issue_pending", None)

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

            # Update the historical retrieval attempt.
            _update_historical_solution_attempt(
                attempt_id=resolution_feedback.get(
                    "historical_attempt_id"
                ),
                chatbot_id=state.get("chatbot_id"),
                resolution_confirmation="yes",
                attempt_status="resolved",
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

            # Mark the historical solution attempt as failed.
            _update_historical_solution_attempt(
                attempt_id=resolution_feedback.get(
                    "historical_attempt_id"
                ),
                chatbot_id=state.get("chatbot_id"),
                resolution_confirmation="no",
                attempt_status="failed",
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
                "historical_attempt_id": resolution_feedback.get("historical_attempt_id"),
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
    current_step = (pending_ticket or {}).get("step", "additional_details")

    # An explicit instruction to submit the pending ticket now is a
    # submission decision, not another request for the same issue details.
    # If no issue was supplied, create a clearly labelled human-follow-up
    # ticket rather than inventing a complaint or looping indefinitely.
    if (
        pending_ticket
        and pending_ticket.get("human_support_requested")
        and is_explicit_immediate_ticket_request(user_message)
        and current_step in {
            "customer_email",
            "human_support_issue_details",
            "additional_details",
            "awaiting_summary_confirmation",
        }
    ):
        email = pending_ticket.get("customer_email") or state.get("customer_email")
        if _ticket_email_required(state.get("company_id"), pending_ticket.get("intent")) and (not email or not valid_email(email)):
            pending_ticket["step"] = "customer_email"
            return _save_and_return(
                state, history, user_message,
                "Absolutely. I can submit the human-support ticket now. "
                "Please provide your email address so the team can contact you.",
                ticket_created=False,
                awaiting_email=True,
                conversation_status="collecting_customer_email",
            )

        pending_ticket["customer_email"] = email
        state["customer_email"] = email
        complaint = (
            pending_ticket.get("issue_summary")
            or pending_ticket.get("original_complaint")
            or ""
        ).strip()

        if not complaint:
            complaint = (
                "Customer explicitly requested immediate human support "
                "but did not provide issue details."
            )
            pending_ticket["original_complaint"] = complaint
            pending_ticket["issue_summary"] = complaint
            pending_ticket["additional_details"] = (
                "The customer repeatedly requested to speak with a human "
                "and explicitly instructed the chatbot to raise a ticket "
                "immediately. No underlying problem details were provided. "
                "Please contact the customer to identify the issue."
            )
            pending_ticket["skip_duplicate_check"] = True
            pending_ticket["intent"] = pending_ticket.get("intent") or "general_enquiry"
            pending_ticket["intervention"] = "HUMAN_ONLY"
            pending_ticket["intervention_confidence"] = 1.0

        pending_ticket["human_support_requested"] = True
        pending_ticket["summary_confirmed"] = True
        return _finish_ticket_creation(
            state, history, user_message, session_id, pending_ticket
        )

    # --------------------------------------------
    # C. Confirm the issue summary
    # --------------------------------------------


    if pending_ticket and current_step == "collecting_custom_fields":
        field_key = pending_ticket.get("current_intake_field")
        field = next((item for item in _get_ticket_intake_fields(state.get("company_id"), pending_ticket.get("intent")) if item.get("key") == field_key), None)
        if not field:
            pending_ticket.pop("current_intake_field", None)
            pending_ticket["step"] = "additional_details"
            return _finish_ticket_creation(state, history, user_message, session_id, pending_ticket)
        value = user_message.strip()
        field_type = field.get("type", "text")
        if field_type == "email":
            if not valid_email(value):
                return _save_and_return(state, history, user_message, "That doesn't look like a valid email address. Could you check it and send it again?", ticket_created=False, awaiting_custom_field=True, conversation_status="collecting_ticket_information")
            pending_ticket["customer_email"] = value
            state["customer_email"] = value
        elif field_type == "phone":
            digits = re.sub(r"\\D", "", value)
            if len(digits) < 7 or len(digits) > 15:
                return _save_and_return(state, history, user_message, "Could you check that phone number and send it again, including the country code if needed?", ticket_created=False, awaiting_custom_field=True, conversation_status="collecting_ticket_information")
            pending_ticket.setdefault("custom_fields", {})[field_key] = value
        elif field_type == "select":
            options = [str(option).strip().lower() for option in field.get("options", [])]
            if value.lower() not in options:
                return _save_and_return(state, history, user_message, "Please choose one of these options: " + ", ".join(str(option) for option in field.get("options", [])), ticket_created=False, awaiting_custom_field=True, conversation_status="collecting_ticket_information")
            pending_ticket.setdefault("custom_fields", {})[field_key] = value
        else:
            pending_ticket.setdefault("custom_fields", {})[field_key] = value
        pending_ticket.pop("current_intake_field", None)
        pending_ticket["step"] = "additional_details"
        return _finish_ticket_creation(state, history, user_message, session_id, pending_ticket)

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
            pending_ticket["summary_confirmed"] = True

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

            # Honour an explicit human handoff instead of diverting
            # the customer into an automated historical-solution suggestion.
            approved_match = None
            if not pending_ticket.get("human_support_requested"):
                try:
                    from services.mcp_client_service import (
                        search_solved_tickets_via_mcp,
                    )

                    approved_match = search_solved_tickets_via_mcp(
                        user_message=complaint,
                        intent=intent,
                        company_id=state.get("company_id"),
                        chatbot_id=state.get("chatbot_id"),
                    )

                    if approved_match and not approved_match.get("found"):
                        approved_match = None

                except Exception as exc:
                    print(f"MCP approved solution retrieval failed: {exc}")
                    approved_match = None
            # If a suitable solution exists, offer it naturally
            if approved_match:

                reply = (
                    "Thanks for clarifying. You can try this:\n\n"
                    f"{approved_match['solution']}\n\n"
                    "Did this resolve the issue? Reply YES or NO."
                )

                # Create a permanent record of this retrieval attempt.
                attempt_id = _create_historical_solution_attempt(
                    state=state,
                    complaint=complaint,
                    matched_ticket=approved_match,
                    response_delivered=reply,
                )

                state["awaiting_resolution_feedback"] = {
                    "complaint": complaint,
                    "intent": intent,
                    "intervention": intervention,
                    "intervention_confidence": intervention_confidence,
                    "matched_ticket": approved_match,
                    "historical_attempt_id": attempt_id,
                }

                state.pop("pending_ticket", None)

                return _save_and_return(
                    state,
                    history,
                    user_message,
                    reply,
                    ticket_created=False,
                    awaiting_resolution_feedback=True,
                    conversation_status="awaiting_resolution_feedback",
                )               

            # Reuse the email collected before complaint validation.
            saved_email = (
                pending_ticket.get("customer_email")
                or state.get("customer_email")
            )
            if saved_email and valid_email(saved_email):
                pending_ticket["customer_email"] = saved_email
                return _finish_ticket_creation(
                    state, history, user_message, session_id, pending_ticket
                )

            return _finish_ticket_creation(
                state, history, user_message, session_id, pending_ticket
            )

        if choice in negative_choices:
            pending_ticket.pop("summary_confirmed", None)
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



    # Do not let repeated human-support requests become issue details.
    # This state is reached only after the customer has supplied an email
    # but has not yet described the actual problem.
    if pending_ticket and current_step == "human_support_issue_details":
        if semantic_human_request:
            pending_ticket["human_support_requested"] = True
            state["human_support_issue_pending"] = True
            escalation_count = int(state.get("human_escalation_count", 0) or 0) + 1
            state["human_escalation_count"] = escalation_count

            email = pending_ticket.get("customer_email") or state.get("customer_email")
            if _ticket_email_required(state.get("company_id"), pending_ticket.get("intent")) and (not email or not valid_email(email)):
                pending_ticket["step"] = "customer_email"
                state["human_escalation_count"] = min(escalation_count, 2)
                return _save_and_return(
                    state, history, user_message,
                    "Of course. What email address should our support team use to contact you?",
                    ticket_created=False,
                    awaiting_email=True,
                    conversation_status="collecting_customer_email",
                )

            pending_ticket["customer_email"] = email
            state["customer_email"] = email

            if escalation_count >= 3:
                issue = (
                    pending_ticket.get("issue_summary")
                    or pending_ticket.get("original_complaint")
                    or ""
                ).strip()
                if not issue:
                    issue = (
                        "Customer repeatedly requested human support but did not provide "
                        "specific issue details. Human support team follow-up is required."
                    )
                    pending_ticket["original_complaint"] = issue
                    pending_ticket["issue_summary"] = issue

                pending_ticket["human_support_requested"] = True
                pending_ticket["summary_confirmed"] = True
                pending_ticket["skip_duplicate_check"] = True
                pending_ticket["intervention"] = "HUMAN_ONLY"
                pending_ticket["intervention_confidence"] = 1.0
                pending_ticket["intent"] = pending_ticket.get("intent") or "general_enquiry"
                return _finish_ticket_creation(
                    state, history, user_message, session_id, pending_ticket
                )

            reply = (
                "Of course. I can arrange that. Could you briefly describe "
                "what you need help with so the team knows how best to assist?"
            )
            return _save_and_return(
                state, history, user_message, reply,
                ticket_created=False,
                awaiting_issue_details=True,
                conversation_status="collecting_support_issue",
            )

        if semantic_category not in {"CUSTOMER_ISSUE", "FOLLOW_UP_ISSUE"}:
            reply = (
                "I'd be happy to help arrange support. Could you tell me "
                "a little about the problem you're experiencing?"
            )
            return _save_and_return(
                state, history, user_message, reply,
                ticket_created=False,
                awaiting_issue_details=True,
                conversation_status="collecting_support_issue",
            )

        complaint = user_message.strip()
        domain_result = _check_company_domain(
            complaint, history, state.get("company_id")
        )
        domain_decision = domain_result.get("decision", "UNCERTAIN")
        print("HUMAN SUPPORT ISSUE DOMAIN DECISION:", domain_decision)

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
                "I can arrange human support. Please explain how this issue relates to this company's products or services.",
                ticket_created=False,
                awaiting_issue_details=True,
                conversation_status="domain_clarification_required",
            )

        try:
            intent_result, intervention_result = _classify_issue(complaint)
        except Exception as exc:
            print(f"Human-support issue classification failed: {exc}")
            return _save_and_return(
                state, history, user_message,
                "I couldn't assess the issue just now. Please try again.",
                ticket_created=False,
                conversation_status="complaint_validation_error",
            )

        state["last_customer_complaint"] = complaint
        state["last_customer_intent"] = intent_result["intent"]
        state["last_intervention"] = intervention_result["intervention"]
        state["last_intervention_confidence"] = intervention_result["confidence"]
        pending_ticket["human_support_requested"] = True

        return _start_ticket_collection(
            state, history, user_message, complaint,
            intent_result["intent"],
            intervention_result["intervention"],
            intervention_result["confidence"],
            _first_investigation_question(complaint),
        )

    # Email collection is handled by its dedicated handler below. Only
    # active investigation steps should enter the ticket interpretation engine.
    if pending_ticket and current_step != "customer_email":

        if current_step == "awaiting_new_issue_confirmation":
            choice = user_message.strip().lower().strip(" .,!?")
            if choice in {"yes", "y", "separate", "separate issue", "yes separate"}:
                candidate = pending_ticket.get("new_issue_candidate", "").strip()
                result = _check_company_domain(candidate, history, state.get("company_id"))
                decision = result.get("decision", "UNCERTAIN")

                if decision == "OUT_OF_DOMAIN":
                    pending_ticket.pop("new_issue_candidate", None)
                    pending_ticket["step"] = "additional_details"
                    return _save_and_return(
                        state, history, user_message,
                        _domain_rejection_message() + "\n\nYour original issue is unchanged.",
                        ticket_created=False,
                        conversation_status="new_issue_out_of_domain",
                    )

                if decision == "UNCERTAIN":
                    pending_ticket["step"] = "awaiting_new_issue_domain_explanation"
                    return _save_and_return(
                        state, history, user_message,
                        "Please explain how this separate problem relates to this company's products or services.",
                        ticket_created=False,
                        conversation_status="new_issue_domain_clarification",
                    )

                state["queued_separate_issue"] = candidate
                pending_ticket.pop("new_issue_candidate", None)
                pending_ticket["step"] = "additional_details"
                return _save_and_return(
                    state, history, user_message,
                    "Understood. I'll keep it separate. Let's finish your current issue first.",
                    ticket_created=False,
                    separate_issue_queued=True,
                    conversation_status="separate_issue_queued",
                )

            if choice in {"no", "n", "nope", "not separate"}:
                pending_ticket.pop("new_issue_candidate", None)
                pending_ticket["step"] = "additional_details"
                return _save_and_return(
                    state, history, user_message,
                    "Okay. I won't add it as a separate issue. Your original complaint remains unchanged.",
                    ticket_created=False,
                    conversation_status="new_issue_declined",
                )

            return _save_and_return(
                state, history, user_message,
                "Please answer YES or NO. Is this a separate issue related to this company's products or services?",
                ticket_created=False,
                awaiting_new_issue_confirmation=True,
                conversation_status="clarifying_new_issue",
            )

        if current_step == "awaiting_new_issue_domain_explanation":
            candidate = pending_ticket.get("new_issue_candidate", "").strip()
            result = _check_company_domain(
                candidate + "\nCustomer explanation: " + user_message.strip(),
                history, state.get("company_id")
            )
            decision = result.get("decision", "UNCERTAIN")

            if decision == "IN_DOMAIN":
                state["queued_separate_issue"] = candidate
                pending_ticket.pop("new_issue_candidate", None)
                pending_ticket["step"] = "additional_details"
                return _save_and_return(
                    state, history, user_message,
                    "Thanks. I'll keep this as a separate support request. Let's finish your current issue first.",
                    ticket_created=False,
                    separate_issue_queued=True,
                    conversation_status="separate_issue_queued",
                )

            if decision == "OUT_OF_DOMAIN":
                pending_ticket.pop("new_issue_candidate", None)
                pending_ticket["step"] = "additional_details"
                return _save_and_return(
                    state, history, user_message,
                    _domain_rejection_message() + "\n\nYour original issue is unchanged.",
                    ticket_created=False,
                    conversation_status="new_issue_out_of_domain",
                )

            return _save_and_return(
                state, history, user_message,
                "I still couldn't confirm the connection. Please explain which company product or service this concerns.",
                ticket_created=False,
                conversation_status="new_issue_domain_clarification",
            )

        # Ensure older pending conversations have the new fields.
        pending_ticket.setdefault("additional_details", "")
        pending_ticket.setdefault("detail_messages", [])
        pending_ticket.setdefault("asked_questions", [])
        pending_ticket.setdefault(
            "issue_summary",
            pending_ticket.get("original_complaint") or "",
        )
        # Count explicit requests for a human while gathering ticket details.
        # The third request triggers ticket creation instead of another loop.
        if current_step == "additional_details" and semantic_human_request:
            pending_ticket["human_support_requested"] = True
            escalation_count = int(state.get("human_escalation_count", 0) or 0) + 1
            state["human_escalation_count"] = escalation_count
            state["human_support_issue_pending"] = True

            email = pending_ticket.get("customer_email") or state.get("customer_email")
            if _ticket_email_required(state.get("company_id"), pending_ticket.get("intent")) and (not email or not valid_email(email)):
                pending_ticket["step"] = "customer_email"
                state["human_escalation_count"] = min(escalation_count, 2)
                return _save_and_return(
                    state, history, user_message,
                    "I understand you'd like a human agent. Please provide your email address so the support team can contact you.",
                    ticket_created=False,
                    awaiting_email=True,
                    conversation_status="collecting_customer_email",
                )

            pending_ticket["customer_email"] = email
            state["customer_email"] = email

            if escalation_count >= 3:
                issue = (
                    pending_ticket.get("issue_summary")
                    or pending_ticket.get("original_complaint")
                    or ""
                ).strip()

                if not issue:
                    issue = (
                        "Customer repeatedly requested human support but did not provide specific issue details."
                    )
                    pending_ticket["original_complaint"] = issue
                    pending_ticket["issue_summary"] = issue
                else:
                    existing_details = (
                        pending_ticket.get("additional_details") or ""
                    ).strip()
                    handoff_note = (
                        "Customer repeatedly requested human support and asked "
                        "to be connected to an agent. Please follow up directly."
                    )
                    pending_ticket["additional_details"] = (
                        existing_details + "\n\n" + handoff_note
                        if existing_details else handoff_note
                    )

                pending_ticket["human_support_requested"] = True
                pending_ticket["summary_confirmed"] = True
                pending_ticket["skip_duplicate_check"] = True
                pending_ticket["intervention"] = "HUMAN_ONLY"
                pending_ticket["intervention_confidence"] = 1.0
                pending_ticket["intent"] = (
                    pending_ticket.get("intent") or "general_enquiry"
                )

                return _finish_ticket_creation(
                    state, history, user_message, session_id, pending_ticket
                )

            # Keep the internal escalation threshold invisible to the customer.
            # Guide the conversation naturally toward the information the agent needs.
            if escalation_count == 1:
                reply = (
                    "Of course. Could you briefly tell me what's happening? "
                    "That will help our support team understand how to assist you."
                )
            else:
                reply = (
                    "Certainly. I can help with that. What problem are you "
                    "experiencing, and when did it start?"
                )
            return _save_and_return(
                state, history, user_message, reply,
                ticket_created=False,
                awaiting_additional_details=True,
                human_escalation_count=escalation_count,
                conversation_status="collecting_additional_details",
            )

        # A human was requested before the customer described the issue.
        if (
            not pending_ticket.get("original_complaint")
            and not pending_ticket.get("detail_messages")
            and not pending_ticket.get("additional_details")
        ):
            domain_result = _check_company_domain(user_message, history, state.get("company_id"))
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
                company_config=_get_active_company_config(state.get("company_id")),
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
       

        print(
            "TICKET INVESTIGATION RESULT:",
            {
                "message": user_message,
                "pending_step": pending_ticket.get("step"),
                "original_complaint": pending_ticket.get("original_complaint"),
                "action": interpretation.get("action"),
                "confidence": interpretation.get("confidence"),
                "next_question": interpretation.get("next_question"),
                "clarification_question": interpretation.get("clarification_question"),
            }
        )

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

        # A short time expression can directly answer when an active
        # complaint occurred. Accept it as a detail instead of asking
        # the customer to explain the same information again.
        message_lower = user_message.lower().strip()
        time_detail_pattern = (
            r"\b(yesterday|today|this morning|this afternoon|"
            r"this evening|last night|last evening|last week|"
            r"this week|a few minutes ago|few minutes ago|"
            r"an hour ago|hours ago|days ago|weeks ago|"
            r"on monday|on tuesday|on wednesday|on thursday|"
            r"on friday|on saturday|on sunday)\b"
        )
        if (
            action == "UNCERTAIN"
            and pending_ticket.get("original_complaint")
            and re.search(time_detail_pattern, message_lower)
        ):
            action = "ADD_DETAIL"
            confidence = max(float(confidence or 0.0), 0.70)
            interpretation["action"] = action
            interpretation["confidence"] = confidence
            interpretation["relevant_details"] = user_message.strip()
            interpretation["needs_clarification"] = False
            interpretation["clarification_question"] = ""
            if not interpretation.get("issue_summary"):
                interpretation["issue_summary"] = (
                    pending_ticket.get("issue_summary")
                    or pending_ticket.get("original_complaint", "")
                )
            print(
                "TICKET DETAIL RECOVERY: accepted time-related detail:",
                user_message,
            )

        # Recover clear customer-reported symptoms when Gemini
        # returns low confidence. Preserve genuine ambiguity.
        if confidence < 0.65 and action == "UNCERTAIN":
            message_lower = user_message.lower().strip()

            payment_words = (
                "payment", "paid", "charge", "charged", "cherged",
                "debit", "debited", "deduct", "deducted", "money",
                "transaction", "amount", "billing"
            )
            clear_symptoms = (
                "twice", "double", "failed", "failure", "declined",
                "deducted", "debited", "not received", "missing",
                "not working", "doesn't work", "does not work",
                "error", "unable", "cannot", "can't", "broken",
                "damaged", "delayed", "not credited"
            )

            is_clear_payment_detail = (
                any(word in message_lower for word in payment_words)
                and any(word in message_lower for word in clear_symptoms)
            )

            if is_clear_payment_detail:
                action = "ADD_DETAIL"
                confidence = 0.70
                interpretation["action"] = "ADD_DETAIL"
                interpretation["confidence"] = confidence
                interpretation["relevant_details"] = user_message.strip()
                interpretation["needs_clarification"] = False
                interpretation["clarification_question"] = ""

                if not interpretation.get("issue_summary"):
                    interpretation["issue_summary"] = (
                        pending_ticket.get("issue_summary")
                        or pending_ticket.get("original_complaint", "")
                    )

                print(
                    "TICKET DETAIL RECOVERY: accepted clear payment symptom:",
                    user_message
                )
            else:
                action = "UNCERTAIN"

        # Focused recovery for a duplicate-charge complaint. This runs
        # regardless of Gemini confidence so short, clear answers such
        # as "charged two times" never fall through to generic chat.
        normalized_payment_text = re.sub(
            r"\s+", " ", user_message.lower()
        ).strip()
        duplicate_charge = (
            any(term in normalized_payment_text for term in (
                "charged twice", "charged two times", "charged 2 times",
                "charged double", "charged more than once",
                "debited twice", "debited two times", "debited 2 times",
                "deducted twice", "deducted two times",
                "deducted 2 times", "money taken twice",
                "charged me twice", "billed twice",
            ))
            or (
                any(term in normalized_payment_text for term in (
                    "two times", "2 times", "twice", "double",
                ))
                and any(term in normalized_payment_text for term in (
                    "charged", "charge", "debited", "deducted",
                    "payment", "billed",
                ))
            )
        )
        print(
            "DUPLICATE PAYMENT TRACE:",
            {
                "message": user_message,
                "matched": duplicate_charge,
                "has_original_complaint": bool(
                    pending_ticket.get("original_complaint")
                ),
                "has_issue_summary": bool(
                    pending_ticket.get("issue_summary")
                ),
                "pending_step": pending_ticket.get("step"),
            },
        )
        if duplicate_charge:
            if not pending_ticket.get("original_complaint"):
                pending_ticket["original_complaint"] = (
                    pending_ticket.get("issue_summary")
                    or "Customer reports a payment issue."
                )
            action = "ADD_DETAIL"
            interpretation["action"] = "ADD_DETAIL"
            interpretation["confidence"] = max(
                float(interpretation.get("confidence") or 0.0), 0.85
            )
            interpretation["relevant_details"] = user_message.strip()
            interpretation["needs_clarification"] = False
            interpretation["clarification_question"] = ""
            interpretation["information_complete"] = False
            interpretation["missing_information"] = [
                "whether both charges were actually deducted",
                "whether one order or two orders were created",
                "transaction date or reference, if available",
            ]
            interpretation["next_question"] = (
                "Were both amounts actually deducted from your bank "
                "or payment account, and did you receive one order "
                "confirmation or two?"
            )
            interpretation["issue_summary"] = (
                (interpretation.get("issue_summary") or "").strip()
                or pending_ticket.get("issue_summary")
                or pending_ticket.get("original_complaint", "")
            )
            print(
                "DUPLICATE PAYMENT INVESTIGATION: targeted follow-up selected"
            )


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
                            "Thanks, I've recorded that detail. "
                            "If you have anything else to add, please share it. "
                            "Otherwise, say 'I'm done' and I'll prepare the issue summary."
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
                            company_id=state.get("company_id"),
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
                    company_id=state.get("company_id"),
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

        if action == "NEW_ISSUE":
            pending_ticket["step"] = "awaiting_new_issue_confirmation"
            pending_ticket["new_issue_candidate"] = user_message.strip()

            reply = (
                "This sounds like a different support problem from your "
                "current issue. I won't combine them into one ticket. "
                "Is this a separate issue related to this company's "
                "products or services? Please answer YES or NO."
            )

            return _save_and_return(
                state, history, user_message, reply,
                ticket_created=False,
                awaiting_new_issue_confirmation=True,
                conversation_status="clarifying_new_issue",
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

        if action == "CANCEL" and not is_ticket_cancellation(user_message):
            # The interpreter can mistake a cancelled order or shipment
            # for withdrawal of the support request. Preserve it as a
            # customer-provided complaint detail instead.
            print(
                "TICKET CANCELLATION GUARD: treating non-support cancellation as issue detail:",
                user_message,
            )
            pending_ticket.setdefault("detail_messages", [])
            pending_ticket.setdefault("additional_details", "")
            current_summary = (
                pending_ticket.get("issue_summary")
                or pending_ticket.get("original_complaint")
                or ""
            ).strip()
            if user_message.strip() and user_message.strip().lower() not in current_summary.lower():
                interpretation["issue_summary"] = (
                    (current_summary + "\n" if current_summary else "")
                    + user_message.strip()
                )
            else:
                interpretation["issue_summary"] = current_summary
            interpretation["action"] = "ADD_DETAIL"
            interpretation["relevant_details"] = user_message.strip()
            interpretation["confidence"] = max(
                float(interpretation.get("confidence") or 0.0), 0.70
            )
            interpretation["information_complete"] = False
            interpretation["missing_information"] = (
                interpretation.get("missing_information") or []
            )
            interpretation["next_question"] = (
                interpretation.get("next_question")
                or "What exact cancellation status or reason is shown in your order details?"
            )
            interpretation["needs_clarification"] = False
            interpretation["clarification_question"] = ""
            action = "ADD_DETAIL"

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

            # Never allow an early "I'm done" to bypass essential
            # investigation. The model must explicitly mark the gathered
            # facts sufficient before summary confirmation can begin.
            if interpretation.get("information_complete") is not True:
                missing = interpretation.get("missing_information") or []
                follow_up = (
                    interpretation.get("next_question")
                    or interpretation.get("clarification_question")
                    or ""
                ).strip()
                if not follow_up and missing:
                    first_missing = str(missing[0]).strip().rstrip(" .?")
                    follow_up = (
                        f"To make sure the support team can investigate, "
                        f"could you share {first_missing}?"
                    )
                if not follow_up:
                    follow_up = (
                        "Before I prepare the summary, I need one more "
                        "useful detail. What happened immediately after "
                        "the issue occurred?"
                    )

                pending_ticket["information_complete"] = False
                pending_ticket["missing_information"] = missing
                return _save_and_return(
                    state,
                    history,
                    user_message,
                    follow_up,
                    ticket_created=False,
                    awaiting_additional_details=True,
                    conversation_status="collecting_additional_details",
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
                company_id=state.get("company_id"),
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

    if pending_ticket and current_step == "customer_email":
        email = user_message.strip()

        if valid_email(email):
            pending_ticket["customer_email"] = email
            state["customer_email"] = email

            if pending_ticket.get("summary_confirmed"):
                return _finish_ticket_creation(
                    state, history, user_message, session_id, pending_ticket
                )

            complaint = (
                pending_ticket.get("original_complaint")
                or pending_ticket.get("issue_summary")
                or ""
            ).strip()

            if not complaint:
                pending_ticket["step"] = "human_support_issue_details"
                pending_ticket["human_support_requested"] = True
                return _save_and_return(
                    state, history, user_message,
                    "Thank you. Now please describe the actual problem you're experiencing so I can prepare an accurate request for the support team.",
                    ticket_created=False,
                    awaiting_issue_details=True,
                    conversation_status="collecting_support_issue",
                )

            domain_result = _check_company_domain(
                complaint, history, state.get("company_id")
            )
            decision = domain_result.get("decision", "UNCERTAIN")
            print("POST-EMAIL COMPLAINT VALIDATION:", decision)

            # Reject only complaints the domain validator confidently marks
            # OUT_OF_DOMAIN. UNCERTAIN is not a rejection: retain the verified
            # customer email and continue investigating the complaint so a
            # short opening such as "I have a payment issue" is not discarded.
            if decision == "OUT_OF_DOMAIN":
                state.pop("pending_ticket", None)
                state["issue_messages"] = []
                state["last_customer_complaint"] = ""
                reply = (
                    _domain_rejection_message()
                    if decision == "OUT_OF_DOMAIN"
                    else
                    "I couldn't verify how this issue relates to our services. "
                    "Could you explain that connection?"
                )
                return _save_and_return(
                    state, history, user_message, reply,
                    ticket_created=False,
                    conversation_status="complaint_not_verified",
                )

            try:
                intent_result, intervention_result = _classify_issue(complaint)
            except Exception as exc:
                print(f"Post-email issue classification failed: {exc}")
                return _save_and_return(
                    state, history, user_message,
                    "I couldn't verify the issue just now. Please try again.",
                    ticket_created=False,
                    conversation_status="complaint_validation_error",
                )

            intent = intent_result["intent"]
            intervention = intervention_result["intervention"]
            confidence = intervention_result["confidence"]

            state["last_customer_complaint"] = complaint
            state["last_customer_intent"] = intent
            state["last_intervention"] = intervention
            state["last_intervention_confidence"] = confidence

            return _start_ticket_collection(
                state, history, user_message, complaint,
                intent, intervention, confidence,
                _first_investigation_question(complaint),
            )

        if semantic_human_request:
            reply = (
                "Your support request is ready for human follow-up. "
                "Please provide your email address so the support team "
                "can contact you."
            )
            return _save_and_return(
                state,
                history,
                user_message,
                reply,
                ticket_created=False,
                awaiting_customer_email=True,
                conversation_status="collecting_customer_email",
            )

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

    # Reuse the early Gemini result whenever it is available.
    needs_gemini_understanding = (
        first_uncertain
        or first_intent == "CUSTOMER_SUPPORT"
        or state.get("human_escalation_count", 0) > 0
    )

    if turn_result is not None:
        category = str(
            turn_result.get("category", "UNCERTAIN")
        ).upper()

    elif needs_gemini_understanding:
        # Retry the existing support/uncertain path if the early call failed.
        try:
            gemini_start = time.perf_counter()
            turn_result = classify_conversation_turn(
                customer_message=user_message,
                conversation_history=history,
                conversation_state=conversation_context,
            )
            print(
                "GEMINI CONVERSATION UNDERSTANDING TIME:",
                f"{time.perf_counter() - gemini_start:.2f}s",
            )
            category = str(
                turn_result.get("category", "UNCERTAIN")
            ).upper()
        except Exception as exc:
            print(f"Conversation understanding failed: {exc}")
            raise HTTPException(
                status_code=503,
                detail="I'm having trouble understanding your message right now. Please try again.",
            )

    else:
        category = {
            "BUSINESS_ENQUIRY": "PRODUCT_ENQUIRY",
            "GENERAL_QUERY": "GENERAL_QUESTION",
        }.get(first_intent, "UNCERTAIN")

    print("FINAL ROUTING CATEGORY:", category)

    # A support intent is not automatically a sufficiently described complaint.
    # Keep vague statements in normal conversation until the customer explains
    # what actually happened; only then begin email collection.
    normalized_issue_message = re.sub(
        r"\s+", " ", user_message.lower()
    ).strip(" .,!?")
    generic_issue_statements = {
        "i have some issue",
        "i have an issue",
        "i have some issues",
        "i have a problem",
        "i have some problem",
        "there is an issue",
        "there is a problem",
        "i am facing an issue",
        "i am facing a problem",
        "facing some issue",
        "facing a problem",
        "some issue",
        "some problem",
        "an issue",
        "a problem",
    }
    topic_only_statement = bool(re.match(
        r"^(?:(?:it|this|that) is )?(?:just )?(?:related to|about|regarding) "
        r"(?:the )?[a-z][a-z /&-]{1,40}$",
        normalized_issue_message,
    ))

    if (
        category in {"CUSTOMER_ISSUE", "FOLLOW_UP_ISSUE"}
        and (
            normalized_issue_message in generic_issue_statements
            or topic_only_statement
        )
    ):
        if "payment" in normalized_issue_message or "billing" in normalized_issue_message:
            reply = (
                "Understood — this is about payment. What exactly happened? "
                "For example, was the payment declined, was money deducted "
                "without confirmation, or were you charged more than once?"
            )
        else:
            reply = (
                "I can help with that. What exactly happened? "
                "Please describe what you were trying to do and what went wrong."
            )

        print(
            "VAGUE COMPLAINT CLARIFICATION:",
            normalized_issue_message,
        )
        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            awaiting_issue_details=True,
            conversation_status="clarifying_complaint",
            response_source="vague_complaint_clarification",
        )
            # ------------------------------------------------

    # ------------------------------------------------
    # HUMAN SUPPORT REQUEST
    # ------------------------------------------------

    explicit_human_request = category == "HUMAN_SUPPORT_REQUEST"

    if explicit_human_request:
        existing_pending = state.get("pending_ticket") or {}
        complaint_parts = []
        existing_complaint = (
            existing_pending.get("issue_summary")
            or existing_pending.get("original_complaint")
        )
        if existing_complaint and str(existing_complaint).strip():
            complaint_parts.append(str(existing_complaint).strip())

        issue_messages = state.get("issue_messages", [])
        if isinstance(issue_messages, list):
            complaint_parts.extend(
                str(item).strip()
                for item in issue_messages
                if item and str(item).strip()
            )
        complaint = " ".join(dict.fromkeys(complaint_parts)).strip()

        email = existing_pending.get("customer_email") or state.get("customer_email")
        pending_ticket = {
            **existing_pending,
            "customer_email": email if email and valid_email(email) else None,
            "original_complaint": complaint,
            "issue_summary": complaint,
            "additional_details": existing_pending.get("additional_details", ""),
            "detail_messages": existing_pending.get("detail_messages", []),
            "asked_questions": existing_pending.get("asked_questions", []),
            "human_support_requested": True,
        }

        if _ticket_email_required(state.get("company_id"), pending_ticket.get("intent")) and (not email or not valid_email(email)):
            pending_ticket["step"] = "customer_email"
            state["pending_ticket"] = pending_ticket
            return _save_and_return(
                state, history, user_message,
                "Certainly. I can arrange human support. Please provide your email address first so the support team can send you updates about your request.",
                ticket_created=False,
                awaiting_email=True,
                conversation_status="collecting_customer_email",
            )

        pending_ticket["customer_email"] = email
        state["customer_email"] = email

        if not complaint:
            pending_ticket["step"] = "human_support_issue_details"
            state["pending_ticket"] = pending_ticket
            return _save_and_return(
                state, history, user_message,
                "Thank you. Now please describe the actual problem you're experiencing. I'll use that information to prepare an accurate request for the human support team.",
                ticket_created=False,
                awaiting_issue_details=True,
                conversation_status="collecting_support_issue",
            )

        domain_result = _check_company_domain(
            complaint, history, state.get("company_id")
        )
        domain_decision = domain_result.get("decision", "UNCERTAIN")
        if domain_decision == "OUT_OF_DOMAIN":
            return _save_and_return(
                state, history, user_message, _domain_rejection_message(),
                ticket_created=False,
                conversation_status="out_of_domain",
                response_source="company_domain_validation",
            )
        if domain_decision == "UNCERTAIN":
            pending_ticket["step"] = "human_support_issue_details"
            state["pending_ticket"] = pending_ticket
            return _save_and_return(
                state, history, user_message,
                "I can arrange human support. Please explain how this issue relates to this company's products or services.",
                ticket_created=False,
                awaiting_issue_details=True,
                conversation_status="domain_clarification_required",
            )

        try:
            intent_result, intervention_result = _classify_issue(complaint)
        except Exception as exc:
            print(f"Human-support issue classification failed: {exc}")
            state["pending_ticket"] = pending_ticket
            return _save_and_return(
                state, history, user_message,
                "I couldn't assess the issue just now. Please try again.",
                ticket_created=False,
                conversation_status="complaint_validation_error",
            )

        state["last_customer_complaint"] = complaint
        state["last_customer_intent"] = intent_result["intent"]
        state["last_intervention"] = intervention_result["intervention"]
        state["last_intervention_confidence"] = intervention_result["confidence"]
        state["pending_ticket"] = pending_ticket
        return _start_ticket_collection(
            state, history, user_message, complaint,
            intent_result["intent"],
            intervention_result["intervention"],
            intervention_result["confidence"],
            _first_investigation_question(complaint),
        )

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
            business_context = (
                "The customer has a business-related enquiry. "
                "Understand the actual subject of the question using the "
                "active company's configuration and knowledge base. "
                "The enquiry may concern products, services, pricing, "
                "availability, features, bookings, demonstrations, or "
                "any other business-specific topic. "
                "Do not assume a particular industry or business domain. "
                "Never invent company-specific information."
            )

        try:
            reply = generate_llm_response(
                customer_message=user_message,
                intent=response_intent,
                context=business_context,
                conversation_history=history,
                company_id=state.get("company_id"),
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

    
    print("FRESH COMPLAINT BRANCH TRACE:", state_key, "pending:", (state.get("pending_ticket") or {}).get("step"))
    if category in {"CUSTOMER_ISSUE", "FOLLOW_UP_ISSUE"} and not state.get("pending_ticket"):
        if category == "CUSTOMER_ISSUE" or not state.get("issue_messages"):
            state["issue_messages"] = [user_message]
        else:
            state["issue_messages"].append(user_message)

        # Keep the issue context bounded to avoid growing the prompt forever.
        state["issue_messages"] = state["issue_messages"][-8:]
        issue_text = " ".join(state["issue_messages"])

        state["pending_ticket"] = {
            "original_complaint": issue_text,
            "issue_summary": issue_text,
            "additional_details": "",
            "detail_messages": [],
            "asked_questions": [],
            "step": "customer_email",
        }
        reply = (
            "I'm sorry you're experiencing this issue. "
            "Please provide your email address so I can verify "
            "the request and help you further."
        )
        return _save_and_return(
            state, history, user_message, reply,
            ticket_created=False,
            awaiting_email=True,
            conversation_status="collecting_customer_email",
        )

        domain_result = _check_company_domain(issue_text, history, state.get("company_id"))
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

        domain_result = _check_company_domain(issue_text, history, state.get("company_id"))
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
        # A low-confidence/unknown classification is NOT a reason to fall
        # back to a generic scripted clarification. Let the conversational
        # model respond to the customer's actual message and recent context.
        # This path must never start, modify, or claim to create a ticket.
        try:
            reply = generate_llm_response(
                customer_message=user_message,
                intent="general_enquiry",
                context=(
                    "The conversation classifier could not confidently assign "
                    "a support action to this message. Continue the conversation "
                    "naturally. First answer the customer's actual question or "
                    "acknowledge what they said. Use the recent conversation to "
                    "understand short replies and references. If the meaning is "
                    "genuinely unclear, ask one specific, conversational "
                    "clarification question. Do not assume this is a complaint, "
                    "do not request an email address, do not start a ticket, and "
                    "do not mention classification or uncertainty."
                ),
                conversation_history=history,
                company_id=state.get("company_id"),
            )
            reply = (reply or "").strip()
            if not reply:
                raise ValueError("Gemini returned an empty conversational response.")
        except Exception as exc:
            print(f"Uncertain-turn conversational response failed: {exc}")
            reply = (
                "I may have misunderstood that. Could you rephrase what "
                "you'd like help with?"
            )

        return _save_and_return(
            state,
            history,
            user_message,
            reply,
            ticket_created=False,
            needs_clarification=False,
            conversation_status="conversation_active",
            response_source="gemini_uncertain_turn_fallback",
        )

    # ------------------------------------------------
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
                company_id=state.get("company_id"),
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
            company_id=state.get("company_id"),
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
app.include_router(historical_solution_router)
app.include_router(historical_attempt_router)
app.include_router(internal_admin_router)


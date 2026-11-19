import hashlib
import os
from pathlib import Path
import uuid
from dotenv import load_dotenv
from zep_cloud.client import Zep
from zep_cloud import AddMessage


load_dotenv()

_client = None
_thread_cache = {}


def _get_client():
    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("ZEP_API_KEY")

    if not api_key:
        print("ZEP: API key not configured.")
        return None

    try:
        _client = Zep(api_key=api_key)
        return _client
    except Exception as exc:
        print(f"ZEP: Client initialization failed: {exc}")
        return None


def _hash_identity(value):
    return hashlib.sha256(
        str(value).encode("utf-8")
    ).hexdigest()


def _get_uuid(obj):
    return (
        getattr(obj, "uuid_", None)
        or getattr(obj, "uuid", None)
    )


def get_or_create_thread(company_id, customer_id, session_id):
    """
    Get a company-isolated Zep user and a thread for this session.

    Customer identity is namespaced by company.
    Thread cache is currently in memory.
    """

    if not company_id or not customer_id or not session_id:
        print("ZEP: Missing identity information.")
        return None

    client = _get_client()

    if client is None:
        return None

    cache_key = _hash_identity(
        f"{company_id}:{customer_id}:{session_id}"
    )

    if cache_key in _thread_cache:
        return _thread_cache[cache_key]

    zep_user_id = "customer_" + _hash_identity(
        f"{company_id}:{customer_id}"
    )

    try:
        # Look up the existing Zep user.
        try:
            user = client.user.lookup(
                user_id=zep_user_id
            )
        except Exception:
            # Create the user if lookup fails.
            user = client.user.create(
                user_id=zep_user_id,
                idempotency_key=str(uuid.uuid4()),
            )

        user_uuid = _get_uuid(user)

        if not user_uuid:
            print("ZEP: Could not obtain user UUID.")
            return None

        # Create a thread for this chat session.
        thread = client.thread.create(
            user_uuid=user_uuid,
            idempotency_key=str(uuid.uuid4()),
        )

        thread_uuid = _get_uuid(thread)

        if not thread_uuid:
            print("ZEP: Could not obtain thread UUID.")
            return None

        _thread_cache[cache_key] = thread_uuid

        return thread_uuid

    except Exception as exc:
        print(f"ZEP: User/thread setup failed: {exc}")
        return None


def add_message(thread_uuid, role, content):
    """Store one message in a Zep thread."""

    if not thread_uuid or not content:
        return False

    client = _get_client()

    if client is None:
        return False

    try:
        client.thread.add_messages(
            thread_uuid,
            messages=[
                AddMessage(
                    role=role,
                    content=str(content)[:4096],
                )
            ],
        )

        return True

    except Exception as exc:
        print(f"ZEP: Message storage failed: {exc}")
        return False


def get_memory_context(thread_uuid):
    """Retrieve relevant memory/context from Zep."""

    if not thread_uuid:
        return ""

    client = _get_client()

    if client is None:
        return ""

    try:
        result = client.thread.get_context(thread_uuid)

        memory_context = getattr(
            result,
            "context",
            "",
        )

        return memory_context or ""

    except Exception as exc:
        print(f"ZEP: Context retrieval failed: {exc}")
        return ""


def start_user_turn(
    company_id,
    customer_id,
    session_id,
    user_message,
):
    """
    Get/create thread, store incoming message,
    and retrieve memory for the current turn.
    """

    thread_uuid = get_or_create_thread(
        company_id=company_id,
        customer_id=customer_id,
        session_id=session_id,
    )

    if not thread_uuid:
        return None, ""

    add_message(
        thread_uuid,
        "user",
        user_message,
    )

    memory_context = get_memory_context(thread_uuid)

    return thread_uuid, memory_context


def save_assistant_turn(thread_uuid, assistant_message):
    """Store the chatbot's generated response."""

    return add_message(
        thread_uuid,
        "assistant",
        assistant_message,
    )

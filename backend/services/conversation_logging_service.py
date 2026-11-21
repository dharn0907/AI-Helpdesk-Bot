from database.database import SessionLocal
from database.models import Conversation, ConversationMessage
from sqlalchemy.sql import func

def save_conversation_exchange(
    session_id,
    company_id,
    customer_id,
    customer_email,
    user_message,
    bot_reply,
):
    """Persist a customer-bot exchange."""

    if not session_id or not company_id:
        print("CONVERSATION LOG: Missing session/company ID.")
        return

    db = SessionLocal()

    try:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.session_id == session_id,
                Conversation.company_id == company_id,
            )
            .first()
        )

        if not conversation:
            conversation = Conversation(
                session_id=session_id,
                company_id=company_id,
                customer_id=customer_id,
                customer_email=customer_email,
                status="Active",
            )

            db.add(conversation)
            db.flush()

        else:
            if customer_id:
                conversation.customer_id = customer_id

            if customer_email:
                conversation.customer_email = customer_email

        if user_message:
            db.add(
                ConversationMessage(
                    conversation_id=conversation.id,
                    sender="customer",
                    content=user_message,
                )
            )

        if bot_reply:
            db.add(
                ConversationMessage(
                    conversation_id=conversation.id,
                    sender="bot",
                    content=bot_reply,
                )
            )

        conversation.last_activity = func.now()

        db.commit()

        print(f"CONVERSATION LOG: Saved {session_id}")

    except Exception as exc:
        db.rollback()
        print(f"CONVERSATION LOG ERROR: {exc}")

    finally:
        db.close()
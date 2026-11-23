import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Float,
)
from sqlalchemy.sql import func

from database.database import Base


class Company(Base):

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)

    slug = Column(String(255), unique=True, nullable=False, index=True)

    bot_public_id = Column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )

    is_active = Column(Boolean, default=True, nullable=False)
    historical_solution_timeout_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    historical_solution_timeout_hours = Column(
        Integer,
        default=24,
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class BotConfiguration(Base):

    __tablename__ = "bot_configurations"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    bot_name = Column(
        String(255),
        nullable=False,
        default="Support Assistant",
    )

    what_this_bot_helps_with = Column(Text, nullable=True)

    about_business = Column(Text, nullable=True)

    how_to_respond = Column(Text, nullable=True)

    when_to_handoff = Column(Text, nullable=True)

    dos = Column(Text, nullable=True)

    donts = Column(Text, nullable=True)

    advanced_instructions = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Ticket(Base):

    __tablename__ = "tickets"

    company_id = Column(
    Integer,
    ForeignKey("companies.id", ondelete="CASCADE"),
    nullable=True,
    index=True,
)

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(String(20), unique=True, index=True)

    session_id = Column(String(100), nullable=True)

    customer_message = Column(Text, nullable=False)

    additional_details = Column(Text, nullable=True)

    customer_email = Column(String(255), nullable=True)

    intent = Column(String(100), nullable=False)

    category = Column(String(100), nullable=True, index=True)

    # Similar ticket grouping
    group_id = Column(String(50), nullable=True, index=True)

    is_master_ticket = Column(Boolean, default=False, nullable=False)

    master_ticket_id = Column(String(20), nullable=True, index=True)

    priority = Column(String(20), default="Medium")

    status = Column(String(30), default="Open")

    agent_reply = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

from sqlalchemy import JSON


class KnowledgeBaseFile(Base):
    __tablename__ = "knowledge_base_files"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_type = Column(String(20), nullable=False)
    row_count = Column(Integer, default=0, nullable=False)
    status = Column(String(30), default="processed", nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class KnowledgeBaseRecord(Base):
    __tablename__ = "knowledge_base_records"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_id = Column(
        Integer,
        ForeignKey("knowledge_base_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    record_data = Column(JSON, nullable=False)
    search_text = Column(Text, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class TicketResolutionReview(Base):

    __tablename__ = "ticket_resolution_reviews"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(
        String(20),
        ForeignKey("tickets.ticket_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    complaint = Column(Text, nullable=False)

    intent = Column(String(100), nullable=False)

    approved_solution = Column(Text, nullable=False)

    approval_status = Column(
        String(20),
        nullable=False,
    )

    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
class Conversation(Base):

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String(100), nullable=False, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    customer_id = Column(String(255), nullable=True)

    customer_email = Column(String(255), nullable=True)

    status = Column(String(30), default="Active", nullable=False)

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    last_activity = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class ConversationMessage(Base):

    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender = Column(
        String(20),
        nullable=False,
    )

    content = Column(Text, nullable=False)

    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
class HistoricalSolutionFeedback(Base):

    __tablename__ = "historical_solution_feedback"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    matched_ticket_id = Column(
        String(20),
        nullable=False,
        index=True,
    )

    customer_complaint = Column(Text, nullable=False)

    reused_solution = Column(Text, nullable=False)

    feedback = Column(
        String(20),
        nullable=False,
    )  # resolved / not_resolved

    similarity_score = Column(Float, nullable=True)

    session_id = Column(String(100), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

class HistoricalSolutionAttempt(Base):

    __tablename__ = "historical_solution_attempts"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    session_id = Column(String(100), nullable=True, index=True)

    customer_email = Column(String(255), nullable=True)

    customer_complaint = Column(Text, nullable=False)

    matched_ticket_id = Column(
        String(20),
        nullable=True,
        index=True,
    )

    retrieved_solution = Column(Text, nullable=True)

    similarity_score = Column(Float, nullable=True)

    response_delivered = Column(Text, nullable=True)

    resolution_confirmation = Column(
        String(20),
        nullable=True,
    )  # yes / no / pending

    attempt_status = Column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
    )  # pending / resolved / failed / ticket_created

    created_ticket_id = Column(
        String(20),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
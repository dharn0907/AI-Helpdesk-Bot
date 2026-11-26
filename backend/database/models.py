import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    BigInteger,
    Float,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from database.database import Base


class Company(Base):

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    email = Column(String(320), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)

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


class CompanyEmailVerification(Base):
    __tablename__ = "company_email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(320), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SupportEmailVerification(Base):
    __tablename__ = "support_email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(320), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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
    chatbot_id = Column(
        BigInteger,
        ForeignKey("chatbots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(String(20), unique=True, index=True)

    session_id = Column(String(100), nullable=True)

    customer_message = Column(Text, nullable=False)

    additional_details = Column(Text, nullable=True)

    customer_email = Column(String(255), nullable=True)

    # Company-configured answers collected by the chatbot (phone, order ID, etc.).
    custom_fields = Column(JSON, nullable=False, default=dict)

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
    chatbot_id = Column(
        BigInteger,
        ForeignKey("chatbots.id", ondelete="SET NULL"),
        nullable=True,
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

    chatbot_id = Column(
        BigInteger,
        ForeignKey("chatbots.id", ondelete="SET NULL"),
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
    chatbot_id = Column(
        BigInteger,
        ForeignKey("chatbots.id", ondelete="SET NULL"),
        nullable=True,
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
# ============================================================
# NEW SUPABASE MODELS
# ============================================================

from sqlalchemy import BigInteger, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    auth_user_id = Column(UUID(as_uuid=False), nullable=True)
    email = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=False, server_default="support_agent")
    status = Column(String, nullable=False, server_default="pending")
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(BigInteger, ForeignKey("organization_members.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Chatbot(Base):
    __tablename__ = "chatbots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    public_id = Column(UUID(as_uuid=False), nullable=False, server_default=func.gen_random_uuid())
    bot_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, server_default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True)
    settings = Column(JSONB, nullable=False, server_default="{}")
    support_email = Column(String, nullable=True)
    support_email_verified = Column(Boolean, nullable=False, server_default="false")
    timezone = Column(String, nullable=True, server_default="Asia/Kolkata")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChatbotChannel(Base):
    __tablename__ = "chatbot_channels"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chatbot_id = Column(BigInteger, ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_type = Column(String, nullable=False)
    channel_name = Column(String, nullable=True)
    channel_identifier = Column(Text, nullable=True)
    configuration = Column(JSONB, nullable=False, server_default="{}")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    chatbot_id = Column(BigInteger, ForeignKey("chatbots.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, server_default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_base_id = Column(BigInteger, ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(Integer, ForeignKey("knowledge_base_files.id", ondelete="CASCADE"), nullable=True)
    record_id = Column(Integer, ForeignKey("knowledge_base_records.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIConfiguration(Base):
    __tablename__ = "ai_configurations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    chatbot_id = Column(BigInteger, ForeignKey("chatbots.id", ondelete="SET NULL"), nullable=True)
    provider = Column(String, nullable=True, server_default="google")
    model_name = Column(String, nullable=True)
    temperature = Column(Numeric, nullable=True, server_default="0.70")
    max_tokens = Column(Integer, nullable=True)
    configuration = Column(JSONB, nullable=False, server_default="{}")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIExecutionLog(Base):
    __tablename__ = "ai_execution_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    chatbot_id = Column(BigInteger, ForeignKey("chatbots.id", ondelete="SET NULL"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    operation = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    status = Column(String, nullable=False, server_default="success")
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    chatbot_id = Column(BigInteger, ForeignKey("chatbots.id", ondelete="SET NULL"), nullable=True)
    model_name = Column(String, nullable=True)
    input_tokens = Column(Integer, nullable=True, server_default="0")
    output_tokens = Column(Integer, nullable=True, server_default="0")
    total_tokens = Column(Integer, nullable=True, server_default="0")
    estimated_cost = Column(Numeric, nullable=True, server_default="0")
    operation = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TicketAssignment(Base):
    __tablename__ = "ticket_assignments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_member_id = Column(BigInteger, ForeignKey("organization_members.id", ondelete="SET NULL"), nullable=True)
    assigned_by = Column(BigInteger, ForeignKey("organization_members.id", ondelete="SET NULL"), nullable=True)
    assignment_status = Column(String, nullable=True, server_default="active")
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    author_member_id = Column(BigInteger, ForeignKey("organization_members.id", ondelete="SET NULL"), nullable=True)
    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, nullable=False, server_default="true")
    comment_type = Column(String, nullable=True, server_default="comment")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)



class TicketConversationSettings(Base):
    """Company-level inactivity policy for interrupted ticket conversations."""

    __tablename__ = "ticket_conversation_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    enabled = Column(Boolean, nullable=False, default=True)
    timeout_minutes = Column(Integer, nullable=False, default=2)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class PendingTicketConversation(Base):
    """Durable state for a ticket-raising conversation awaiting customer input."""

    __tablename__ = "pending_ticket_conversations"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "chatbot_id",
            "session_id",
            name="uq_pending_ticket_conversation_scope",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chatbot_id = Column(
        BigInteger,
        ForeignKey("chatbots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(String(100), nullable=False, index=True)
    customer_id = Column(String(255), nullable=True, index=True)
    customer_email = Column(String(255), nullable=True, index=True)
    state_data = Column(JSON, nullable=False)
    status = Column(String(30), nullable=False, default="active", index=True)
    last_activity = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

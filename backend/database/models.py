
"""Database models for the helpdesk system."""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from database.database import Base


class Ticket(Base):

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(String(20), unique=True, index=True)

    session_id = Column(String(100), nullable=True)

    customer_message = Column(Text, nullable=False)

    intent = Column(String(100), nullable=False)

    priority = Column(String(20), default="Medium")

    status = Column(String(30), default="Open")

    agent_reply = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

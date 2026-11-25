from pathlib import Path

p = Path("backend/routes/conversation_routes.py")
s = p.read_text(encoding="utf-8")

# 1. Make chatbot_id optional in GET routes
s = s.replace(
    "def get_conversations(\n    chatbot_id: int,",
    "def get_conversations(\n    chatbot_id: int | None = None,"
)
s = s.replace(
    "def get_conversation_details(\n    conversation_id: int,\n    chatbot_id: int,",
    "def get_conversation_details(\n    conversation_id: int,\n    chatbot_id: int | None = None,"
)

# 2. Replace the conversation-list route
start = s.index('@router.get("/")')
end = s.index("# Get a particular conversation", start)

list_route = '''@router.get("/")
def get_conversations(
    chatbot_id: int | None = None,
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
    agent_email: str = Header(default=None, alias="X-Agent-Email"),
):
    db = SessionLocal()
    try:
        company = get_request_company(db, authorization, x_company_id, agent_email)

        if not company:
            raise HTTPException(404, "Company not found")

        query = db.query(Conversation).filter(
            Conversation.company_id == company["id"]
        )

        if agent_email:
            # Agents can view conversations belonging to their company.
            pass
        else:
            if chatbot_id is None:
                raise HTTPException(400, "chatbot_id is required")
            chatbot = db.query(Chatbot).filter(
                Chatbot.id == chatbot_id,
                Chatbot.organization_id == company["id"],
                Chatbot.status == "active",
            ).first()
            if not chatbot:
                raise HTTPException(404, "Chatbot not found")
            query = query.filter(Conversation.chatbot_id == chatbot_id)

        conversations = query.order_by(
            Conversation.last_activity.desc()
        ).all()

        result = []
        for conversation in conversations:
            messages = (
                db.query(ConversationMessage)
                .filter(ConversationMessage.conversation_id == conversation.id)
                .order_by(ConversationMessage.timestamp.asc())
                .all()
            )
            result.append({
                "id": conversation.id,
                "session_id": conversation.session_id,
                "customer_id": conversation.customer_id,
                "customer_email": conversation.customer_email,
                "status": conversation.status,
                "started_at": conversation.started_at,
                "last_activity": conversation.last_activity,
                "message_count": len(messages),
                "last_message": messages[-1].content if messages else None,
            })
        return result
    finally:
        db.close()


'''

s = s[:start] + list_route + s[end:]

# 3. Replace conversation detail route
start = s.index('@router.get("/{conversation_id}")')
end = s.index("# Edit an approved historical solution", start)

detail_route = '''@router.get("/{conversation_id}")
def get_conversation_details(
    conversation_id: int,
    chatbot_id: int | None = None,
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
    agent_email: str = Header(default=None, alias="X-Agent-Email"),
):
    db = SessionLocal()
    try:
        company = get_request_company(db, authorization, x_company_id, agent_email)

        if not company:
            raise HTTPException(404, "Company not found")

        if agent_email:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.company_id == company["id"],
            ).first()
        else:
            if chatbot_id is None:
                raise HTTPException(400, "chatbot_id is required")
            conversation = get_conversation_for_company(
                db, conversation_id, company, chatbot_id
            )

        if not conversation:
            raise HTTPException(404, "Conversation not found")

        messages = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation.id)
            .order_by(ConversationMessage.timestamp.asc())
            .all()
        )

        reviews = (
            db.query(TicketResolutionReview)
            .join(Ticket, Ticket.ticket_id == TicketResolutionReview.ticket_id)
            .filter(
                Ticket.session_id == conversation.session_id,
                TicketResolutionReview.company_id == company["id"],
                TicketResolutionReview.approval_status == "approved",
                TicketResolutionReview.approved_solution != "",
            )
            .order_by(TicketResolutionReview.created_at.desc())
            .all()
        )

        return {
            "id": conversation.id,
            "session_id": conversation.session_id,
            "customer_id": conversation.customer_id,
            "customer_email": conversation.customer_email,
            "status": conversation.status,
            "started_at": conversation.started_at,
            "last_activity": conversation.last_activity,
            "messages": [
                {
                    "id": message.id,
                    "sender": message.sender,
                    "content": message.content,
                    "timestamp": message.timestamp,
                }
                for message in messages
            ],
            "historical_solutions": [
                {
                    "ticket_id": review.ticket_id,
                    "complaint": review.complaint,
                    "intent": review.intent,
                    "approved_solution": review.approved_solution,
                    "approval_status": review.approval_status,
                }
                for review in reviews
            ],
        }
    finally:
        db.close()


'''

s = s[:start] + detail_route + s[end:]

# 4. Replace historical-solution edit route
start = s.index('@router.patch("/{conversation_id}/historical-solutions/{ticket_id}")')
end = s.index("# Delete an approved historical solution", start)

patch_route = '''@router.patch("/{conversation_id}/historical-solutions/{ticket_id}")
def update_historical_solution(
    conversation_id: int,
    ticket_id: str,
    data: dict,
    chatbot_id: int | None = None,
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
    agent_email: str = Header(default=None, alias="X-Agent-Email"),
):
    db = SessionLocal()
    try:
        company = get_request_company(db, authorization, x_company_id, agent_email)

        if not company:
            raise HTTPException(404, "Company not found")

        if agent_email:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.company_id == company["id"],
            ).first()
        else:
            if chatbot_id is None:
                raise HTTPException(400, "chatbot_id is required")
            conversation = get_conversation_for_company(
                db, conversation_id, company, chatbot_id
            )

        if not conversation:
            raise HTTPException(404, "Conversation not found")

        ticket = db.query(Ticket).filter(
            Ticket.ticket_id == ticket_id,
            Ticket.session_id == conversation.session_id,
        ).first()

        if not ticket:
            raise HTTPException(404, "Ticket not found for this conversation")

        review = db.query(TicketResolutionReview).filter(
            TicketResolutionReview.ticket_id == ticket_id,
            TicketResolutionReview.company_id == company["id"],
            TicketResolutionReview.approval_status == "approved",
        ).first()

        if not review:
            raise HTTPException(404, "Approved historical solution not found")

        solution = str(data.get("approved_solution", "")).strip()
        if not solution:
            raise HTTPException(400, "Solution cannot be empty")

        review.approved_solution = solution
        db.commit()
        db.refresh(review)

        return {
            "message": "Historical solution updated successfully.",
            "ticket_id": ticket_id,
            "approved_solution": review.approved_solution,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


'''

s = s[:start] + patch_route + s[end:]

# 5. Replace historical-solution delete route
start = s.index('@router.delete("/{conversation_id}/historical-solutions/{ticket_id}")')

delete_route = '''@router.delete("/{conversation_id}/historical-solutions/{ticket_id}")
def delete_historical_solution(
    conversation_id: int,
    ticket_id: str,
    chatbot_id: int | None = None,
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
    agent_email: str = Header(default=None, alias="X-Agent-Email"),
):
    db = SessionLocal()
    try:
        company = get_request_company(db, authorization, x_company_id, agent_email)

        if not company:
            raise HTTPException(404, "Company not found")

        if agent_email:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.company_id == company["id"],
            ).first()
        else:
            if chatbot_id is None:
                raise HTTPException(400, "chatbot_id is required")
            conversation = get_conversation_for_company(
                db, conversation_id, company, chatbot_id
            )

        if not conversation:
            raise HTTPException(404, "Conversation not found")

        ticket = db.query(Ticket).filter(
            Ticket.ticket_id == ticket_id,
            Ticket.session_id == conversation.session_id,
        ).first()

        if not ticket:
            raise HTTPException(404, "Ticket not found for this conversation")

        review = db.query(TicketResolutionReview).filter(
            TicketResolutionReview.ticket_id == ticket_id,
            TicketResolutionReview.company_id == company["id"],
            TicketResolutionReview.approval_status == "approved",
        ).first()

        if not review:
            raise HTTPException(404, "Approved historical solution not found")

        db.delete(review)
        db.commit()

        return {
            "message": "Historical solution deleted successfully.",
            "ticket_id": ticket_id,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
'''

s = s[:start] + delete_route + "\\n"

p.write_text(s, encoding="utf-8")
print("Backend routes rewritten.")

from pathlib import Path
import shutil

path = Path("backend/routes/internal_admin_routes.py")
source = path.read_text(encoding="utf-8")
backup = path.with_name("internal_admin_routes.py.before_ticket_conversation_filter.bak")

replacements = [
    (
        'router = APIRouter(prefix="/api/internal", tags=["Internal Admin"])\n',
        'router = APIRouter(prefix="/api/internal", tags=["Internal Admin"])\n\n\n'
        'def _ticket_session_ids(db):\n'
        '    """Session IDs belonging to successfully created support tickets."""\n'
        '    return db.query(Ticket.session_id).filter(Ticket.session_id.isnot(None))\n'
    ),
    (
        '"conversations": db.query(Conversation).count(),',
        '"conversations": db.query(Conversation).filter(Conversation.session_id.in_(_ticket_session_ids(db))).count(),'
    ),
    (
        '"total_conversations": db.query(Conversation).count(),',
        '"total_conversations": db.query(Conversation).filter(Conversation.session_id.in_(_ticket_session_ids(db))).count(),'
    ),
    (
        '"conversations": db.query(Conversation).filter(Conversation.company_id == row.id).count(),',
        '"conversations": db.query(Conversation).filter(Conversation.company_id == row.id, Conversation.session_id.in_(_ticket_session_ids(db))).count(),'
    ),
    (
        '"conversations": db.query(Conversation).filter(Conversation.chatbot_id == row.id).count(),',
        '"conversations": db.query(Conversation).filter(Conversation.chatbot_id == row.id, Conversation.session_id.in_(_ticket_session_ids(db))).count(),'
    ),
    (
        '    ).outerjoin(Chatbot, Chatbot.id == Conversation.chatbot_id).order_by(\n'
        '        Conversation.last_activity.desc()\n'
        '    ).limit(500).all()',
        '    ).outerjoin(Chatbot, Chatbot.id == Conversation.chatbot_id).filter(\n'
        '        Conversation.session_id.in_(_ticket_session_ids(db))\n'
        '    ).order_by(\n'
        '        Conversation.last_activity.desc()\n'
        '    ).limit(500).all()'
    ),
]

for old, new in replacements:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"STOPPED: expected 1 match, found {count}: {old[:80]!r}")
    source = source.replace(old, new, 1)

shutil.copy2(path, backup)
path.write_text(source, encoding="utf-8")

print("PATCH APPLIED")
print(f"Backup created: {backup}")

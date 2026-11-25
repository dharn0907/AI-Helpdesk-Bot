from pathlib import Path

p = Path("backend/routes/conversation_routes.py")
s = p.read_text(encoding="utf-8")

# Add OrganizationMember import
if "    OrganizationMember," not in s:
    s = s.replace(
        "    Chatbot,\n)",
        "    Chatbot,\n    OrganizationMember,\n)",
        1
    )

# Add approved-agent company resolver
helper = '''

def get_agent_company(db, email):
    email = str(email or "").strip().lower()
    member = db.query(OrganizationMember).filter(
        OrganizationMember.email == email,
        OrganizationMember.role == "support_agent",
        OrganizationMember.status == "approved",
    ).first()

    if not member:
        raise HTTPException(401, "Approved agent not found.")

    return {"id": member.organization_id}


def get_request_company(db, authorization, x_company_id, agent_email):
    if agent_email:
        return get_agent_company(db, agent_email)
    return get_workspace_company(authorization, x_company_id, db)
'''

if "def get_agent_company(" not in s:
    marker = "def get_conversation_for_company(db, conversation_id, company, chatbot_id):"
    if marker not in s:
        raise SystemExit("Could not find conversation helper. No changes saved.")
    pos = s.index("\n\n", s.index("        .first()", s.index(marker)))
    s = s[:pos] + helper + s[pos:]

# Add agent_email to all four endpoints and resolve company through shared helper
for fn in (
    "get_conversations",
    "get_conversation_details",
    "update_historical_solution",
    "delete_historical_solution",
):
    start = s.index("def " + fn + "(")
    end = s.index("):", start)
    block = s[start:end]

    if "agent_email:" not in block:
        block += "\n    agent_email: str = Header(default=None, alias='X-Agent-Email'),"
        s = s[:start] + block + s[end:]

# Replace company resolution in all endpoint bodies
s = s.replace(
    "company = get_workspace_company(authorization, x_company_id, db)",
    "company = get_request_company(db, authorization, x_company_id, agent_email)",
)

# Add chatbot_id to historical solution routes
for fn in ("update_historical_solution", "delete_historical_solution"):
    start = s.index("def " + fn + "(")
    end = s.index("):", start)
    block = s[start:end]
    if "chatbot_id: int" not in block:
        block = block.replace(
            "    ticket_id: str,",
            "    ticket_id: str,\n    chatbot_id: int,",
            1
        )
        s = s[:start] + block + s[end:]

s = s.replace(
    "db, conversation_id, company\n            )",
    "db, conversation_id, company, chatbot_id\n        )"
)

# Ensure chatbot belongs to the resolved company on agent routes too
needle = '        if not company:\n            raise HTTPException(status_code=404, detail="Company not found")'
replacement = needle + '''

        chatbot = db.query(Chatbot).filter(
            Chatbot.id == chatbot_id,
            Chatbot.organization_id == company["id"],
            Chatbot.status == "active",
        ).first()
        if not chatbot:
            raise HTTPException(404, "Chatbot not found")
'''
s = s.replace(needle, replacement, 1)

p.write_text(s, encoding="utf-8")
print("Backend conversation routes updated.")

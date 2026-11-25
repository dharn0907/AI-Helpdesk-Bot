from pathlib import Path
import re
import shutil

bp = Path("backend/routes/ticket_routes.py")
fp = Path("agent-frontend/src/services/ticketApi.js")
b = bp.read_text(encoding="utf-8")
f = fp.read_text(encoding="utf-8")

names = [
    "get_ticket",
    "update_ticket",
    "review_ticket_resolution",
    "get_ticket_resolution_review",
    "summarize_ticket",
    "get_similar_tickets",
]

# Build and validate all changes in memory before writing.
if "def get_agent_company(db, email, company_id):" not in b:
    marker = "def get_scoped_ticket(db, ticket_id, chatbot_id):"
    if marker not in b:
        raise SystemExit("STOP: Ticket helper location not found.")
    helper = '''def get_agent_company(db, email, company_id):
    email = str(email or "").strip().lower()

    if not email or not company_id:
        raise HTTPException(401, "Agent email or company ID is missing.")

    member = db.query(OrganizationMember).filter(
        OrganizationMember.email == email,
        OrganizationMember.organization_id == company_id,
        OrganizationMember.role == "support_agent",
        OrganizationMember.status == "approved",
    ).first()

    if not member:
        raise HTTPException(401, "Approved agent membership not found for this company.")

    return {"id": member.organization_id}


'''
    b = b.replace(marker, helper + marker, 1)

for name in names:
    start = b.find(f"def {name}(")
    if start < 0:
        raise SystemExit(f"STOP: Function {name} not found.")

    end = b.find("\n@router.", start)
    if end < 0:
        end = len(b)

    block = b[start:end]

    if "chatbot_id: int," not in block:
        raise SystemExit(f"STOP: chatbot_id signature not found in {name}.")
    block = block.replace("chatbot_id: int,", "chatbot_id: int = None,", 1)

    company_header = re.compile(
        r"(    x_company_id: int = Header\(default=None, alias=[\"']X-Company-ID[\"']\)\n)"
    )
    block, n = company_header.subn(
        r"\1    agent_email: str = Header(default=None, alias='X-Agent-Email'),\n",
        block,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"STOP: Company header not found in {name}.")

    old_scope = (
        "    company = get_workspace_company(authorization, x_company_id, db)\n"
        "    ticket = get_scoped_ticket(db, ticket_id, chatbot_id)"
    )
    new_scope = '''    if agent_email:
        company = get_agent_company(db, agent_email, x_company_id)
        ticket = db.query(Ticket).filter(
            Ticket.ticket_id == ticket_id,
            Ticket.company_id == company["id"],
        ).first()
    else:
        if chatbot_id is None:
            raise HTTPException(422, "chatbot_id is required.")
        company = get_workspace_company(authorization, x_company_id, db)
        ticket = get_scoped_ticket(db, ticket_id, chatbot_id)'''

    if old_scope not in block:
        raise SystemExit(f"STOP: Ticket scope block not found in {name}.")
    block = block.replace(old_scope, new_scope, 1)
    b = b[:start] + block + b[end:]

# Scope the agent ticket list by the company in the agent session.
old_list = '''    member = db.query(OrganizationMember).filter(
        OrganizationMember.email == email,
        OrganizationMember.role == "support_agent",
        OrganizationMember.status == "approved",
    ).first()'''
new_list = '''    company_id = data.get("company_id")

    member = db.query(OrganizationMember).filter(
        OrganizationMember.email == email,
        OrganizationMember.organization_id == company_id,
        OrganizationMember.role == "support_agent",
        OrganizationMember.status == "approved",
    ).first()'''

if old_list not in b:
    raise SystemExit("STOP: Agent ticket-list lookup did not match.")
b = b.replace(old_list, new_list, 1)

# Frontend agent session helper.
old_helper = '''const getAgentEmail = () => {
  const agent = JSON.parse(sessionStorage.getItem("agent") || "null");

  if (!agent?.email) {
    throw new Error("Agent session not found. Please log in again.");
  }

  return agent.email;
};'''
new_helper = '''const getAgent = () => {
  const agent = JSON.parse(sessionStorage.getItem("agent") || "null");

  if (!agent?.email || !agent?.company_id) {
    throw new Error("Agent session or company not found. Please log in again.");
  }

  return agent;
};

const getAgentEmail = () => getAgent().email;

const getAgentHeaders = () => {
  const agent = getAgent();
  return {
    "X-Agent-Email": agent.email,
    "X-Company-ID": String(agent.company_id),
  };
};'''

if old_helper not in f:
    raise SystemExit("STOP: Frontend agent helper did not match.")
f = f.replace(old_helper, new_helper, 1)

# Ticket list: include company ID.
old_body = 'body: JSON.stringify({ email: getAgentEmail() }),'
if old_body not in f:
    raise SystemExit("STOP: Agent ticket-list request did not match.")
f = f.replace(
    old_body,
    'body: JSON.stringify({ email: getAgentEmail(), company_id: getAgent().company_id }),',
    1,
)

# Ticket detail GET.
old = 'fetch(`${API_BASE_URL}/tickets/${ticketId}`);'
if old not in f:
    raise SystemExit("STOP: Ticket detail GET did not match.")
f = f.replace(
    old,
    'fetch(`${API_BASE_URL}/tickets/${ticketId}`, { headers: getAgentHeaders() });',
    1,
)

# Ticket update PATCH.
old = '''headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),'''
if old not in f:
    raise SystemExit("STOP: Ticket update request did not match.")
f = f.replace(
    old,
    '''headers: {
      "Content-Type": "application/json",
      ...getAgentHeaders(),
    },
    body: JSON.stringify(data),''',
    1,
)

# Resolution review POST and summary POST.
old = 'headers: { "Content-Type": "application/json" },'
if f.count(old) < 2:
    raise SystemExit("STOP: Expected review/summary POST headers not found.")
f = f.replace(
    old,
    'headers: { "Content-Type": "application/json", ...getAgentHeaders() },',
    2,
)

# Resolution review GET and similar tickets GET.
old_review = '''`${API_BASE_URL}/tickets/${ticketId}/resolution-review`
  );'''
new_review = '''`${API_BASE_URL}/tickets/${ticketId}/resolution-review`,
    { headers: getAgentHeaders() }
  );'''
if old_review not in f:
    raise SystemExit("STOP: Resolution review GET did not match.")
f = f.replace(old_review, new_review, 1)

old_similar = '''`${API_BASE_URL}/tickets/${ticketId}/similar`
  );'''
new_similar = '''`${API_BASE_URL}/tickets/${ticketId}/similar`,
    { headers: getAgentHeaders() }
  );'''
if old_similar not in f:
    raise SystemExit("STOP: Similar tickets GET did not match.")
f = f.replace(old_similar, new_similar, 1)

# Final checks before writing.
if b.count("agent_email: str = Header(default=None, alias='X-Agent-Email')") < 6:
    raise SystemExit("STOP: Backend agent headers validation failed.")
if f.count("getAgentHeaders()") < 6:
    raise SystemExit("STOP: Frontend header validation failed.")

shutil.copy2(bp, str(bp) + ".ticket_fix.bak")
shutil.copy2(fp, str(fp) + ".ticket_fix.bak")
bp.write_text(b, encoding="utf-8")
fp.write_text(f, encoding="utf-8")

print("PATCH APPLIED")
print("Updated six ticket detail endpoints.")
print("Added company-scoped agent membership validation.")
print("Updated agent ticket API headers.")

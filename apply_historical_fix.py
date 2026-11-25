from pathlib import Path

root = Path(r"D:\bot\AI-Helpdesk-Bot")

# Backend: validate the agent against the exact company ID.
old_helper = '''def get_agent_company(db, email):
    email = str(email or "").strip().lower()

    member = db.query(OrganizationMember).filter(
        OrganizationMember.email == email,
        OrganizationMember.role == "support_agent",
        OrganizationMember.status == "approved",
    ).first()

    if not member:
        raise HTTPException(
            status_code=401,
            detail="Approved agent not found."
        )

    return {"id": member.organization_id}
'''

new_helper = '''def get_agent_company(db, email, company_id):
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

for name in [
    "backend/routes/historical_solution_routes.py",
    "backend/routes/historical_attempt_routes.py",
]:
    p = root / name
    s = p.read_text(encoding="utf-8-sig")
    if old_helper not in s:
        raise SystemExit("Expected backend helper not found in " + name)
    s = s.replace(old_helper, new_helper, 1)
    s = s.replace(
        "return get_agent_company(db, agent_email)",
        "return get_agent_company(db, agent_email, x_company_id)",
        1
    )
    p.write_text(s, encoding="utf-8")

# Frontend shared helper.
helper = '''
function getAgentHeaders() {
  const agent = JSON.parse(sessionStorage.getItem("agent") || "null");
  if (!agent?.email || !agent?.company_id) {
    throw new Error("Agent session or company not found. Please log in again.");
  }
  return {
    "X-Agent-Email": agent.email,
    "X-Company-ID": String(agent.company_id),
  };
}
'''

p = root / "agent-frontend/src/pages/HistoricalSolutions.jsx"
s = p.read_text(encoding="utf-8-sig")
api = 'const API = "http://127.0.0.1:8000";'
if api not in s:
    raise SystemExit("Solutions API declaration not found")
s = s.replace(api, api + "\n" + helper, 1)

s = s.replace(
    'fetch(`${API}/historical-solutions/`);',
    'fetch(`${API}/historical-solutions/`, { headers: getAgentHeaders() });',
    1
)

s = s.replace(
    '"Content-Type": "application/json",',
    '"Content-Type": "application/json",\n            ...getAgentHeaders(),',
    1
)

s = s.replace(
    'method: "DELETE",',
    'method: "DELETE",\n          headers: getAgentHeaders(),',
    1
)

if "getAgentHeaders()" not in s:
    raise SystemExit("Solutions frontend patch did not apply")
p.write_text(s, encoding="utf-8")

p = root / "agent-frontend/src/pages/HistoricalSolutionAttempts.jsx"
s = p.read_text(encoding="utf-8-sig")
if api not in s:
    raise SystemExit("Attempts API declaration not found")
s = s.replace(api, api + "\n" + helper, 1)

old = '''        `${API}/historical-solution-attempts/`
      );'''
new = '''        `${API}/historical-solution-attempts/`,
        { headers: getAgentHeaders() }
      );'''
if old not in s:
    raise SystemExit("Attempts GET request not found")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

print("PATCH APPLIED")

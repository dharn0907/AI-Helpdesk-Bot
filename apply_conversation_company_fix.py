from pathlib import Path
import shutil

backend = Path("backend/routes/conversation_routes.py")
frontend = Path("agent-frontend/src/pages/Conversations.jsx")

b = backend.read_text(encoding="utf-8")
f = frontend.read_text(encoding="utf-8")

old_backend = '''def get_agent_company(db, email):
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
    return get_workspace_company(authorization, x_company_id, db)'''

new_backend = '''def get_agent_company(db, email, company_id):
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


def get_request_company(db, authorization, x_company_id, agent_email):
    if agent_email:
        return get_agent_company(db, agent_email, x_company_id)
    return get_workspace_company(authorization, x_company_id, db)'''

old_frontend_helper = '''function getAgentHeaders() {
  const agent = JSON.parse(sessionStorage.getItem("agent") || "null");
  if (!agent?.email) {
    throw new Error("Agent session not found. Please log in again.");
  }
  return { "X-Agent-Email": agent.email };
}'''

new_frontend_helper = '''function getAgentHeaders() {
  const agent = JSON.parse(sessionStorage.getItem("agent") || "null");
  if (!agent?.email || !agent?.company_id) {
    throw new Error("Agent session or company not found. Please log in again.");
  }
  return {
    "X-Agent-Email": agent.email,
    "X-Company-ID": String(agent.company_id),
  };
}'''

old_save_headers = '''          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            approved_solution: trimmedSolution,
          }),'''

new_save_headers = '''          headers: {
            "Content-Type": "application/json",
            ...getAgentHeaders(),
          },
          body: JSON.stringify({
            approved_solution: trimmedSolution,
          }),'''

if b.count(old_backend) != 1:
    raise SystemExit("STOP: Backend helper did not match exactly once. No files changed.")

if f.count(old_frontend_helper) != 1:
    raise SystemExit("STOP: Frontend helper did not match exactly once. No files changed.")

if f.count(old_save_headers) != 1:
    raise SystemExit("STOP: Save-solution request did not match exactly once. No files changed.")

shutil.copy2(backend, str(backend) + ".conversation_company_fix.bak")
shutil.copy2(frontend, str(frontend) + ".conversation_company_fix.bak")

b = b.replace(old_backend, new_backend, 1)
f = f.replace(old_frontend_helper, new_frontend_helper, 1)
f = f.replace(old_save_headers, new_save_headers, 1)

backend.write_text(b, encoding="utf-8")
frontend.write_text(f, encoding="utf-8")

print("PATCH APPLIED")
print("Conversation backend now validates email + company ID.")
print("Conversation frontend sends both headers, including when editing solutions.")

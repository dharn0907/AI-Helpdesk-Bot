from pathlib import Path

p = Path("backend/routes/ticket_routes.py")
s = p.read_text(encoding="utf-8")

start = s.index("def support_agent_login(")
end = s.index("\n\n@router.post", start)

block = s[start:end]

old = '''    company_id = data.get("company_id")

    member = db.query(OrganizationMember).filter(
        OrganizationMember.email == email,
        OrganizationMember.organization_id == company_id,
        OrganizationMember.role == "support_agent",
        OrganizationMember.status == "approved",
    ).first()'''

new = '''    member = db.query(OrganizationMember).filter(
        OrganizationMember.email == email,
        OrganizationMember.role == "support_agent",
        OrganizationMember.status == "approved",
    ).first()'''

if old not in block:
    raise SystemExit("STOP: Expected modified login lookup was not found.")

block = block.replace(old, new, 1)
s = s[:start] + block + s[end:]

p.write_text(s, encoding="utf-8")
print("LOGIN REPAIRED")

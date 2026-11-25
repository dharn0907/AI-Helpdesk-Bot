from pathlib import Path

p = Path("backend/routes/company_routes.py")
s = p.read_text(encoding="utf-8")

old = """    bots = db.query(Chatbot).filter(
        Chatbot.organization_id == company['id']
    ).order_by(Chatbot.id.desc()).all()
"""

new = """    bots = db.query(Chatbot).filter(
        Chatbot.organization_id == company['id'],
        Chatbot.status != "inactive"
    ).order_by(Chatbot.id.desc()).all()
"""

if old not in s:
    raise SystemExit("Could not find the exact chatbot list query. No changes made.")

p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("SUCCESS: Inactive chatbots are now hidden from the chatbot list.")

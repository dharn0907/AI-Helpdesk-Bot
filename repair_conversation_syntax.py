from pathlib import Path

p = Path("backend/routes/conversation_routes.py")
s = p.read_text(encoding="utf-8")

if s.endswith("\\n"):
    s = s[:-2] + "\n"

p.write_text(s, encoding="utf-8")
print("Removed invalid trailing characters.")

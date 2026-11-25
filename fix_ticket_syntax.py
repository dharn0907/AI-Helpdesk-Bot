from pathlib import Path
import re

p = Path("backend/routes/ticket_routes.py")
s = p.read_text(encoding="utf-8")

pattern = re.compile(
    r"(x_company_id: int = Header\(default=None, alias=['\"]X-Company-ID['\"]\))\n"
    r"(\s+agent_email: str = Header\(default=None, alias='X-Agent-Email'\),)"
)

s, count = pattern.subn(r"\1,\n\2", s)

if count != 6:
    raise SystemExit(f"Expected 6 fixes, found {count}. File not written.")

p.write_text(s, encoding="utf-8")
print(f"Fixed {count} missing commas.")

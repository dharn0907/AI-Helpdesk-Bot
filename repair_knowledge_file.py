from pathlib import Path
import subprocess
import shutil

p = Path("backend/routes/knowledge_base_routes.py")

# Preserve the damaged version before restoring.
shutil.copy2(p, p.with_suffix(".py.corrupted_backup"))

result = subprocess.run(
    ["git", "show", "HEAD:backend/routes/knowledge_base_routes.py"],
    capture_output=True,
    text=True,
    encoding="utf-8"
)

if result.returncode != 0:
    raise SystemExit("Could not retrieve the committed original file.")

p.write_text(result.stdout, encoding="utf-8")
print("Restored knowledge_base_routes.py from Git.")

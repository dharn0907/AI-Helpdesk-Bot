from pathlib import Path
import shutil

path = Path("main.py")
source = path.read_text(encoding="utf-8")

backup = Path("main.py.before_human_support_fix.bak")
shutil.copy2(path, backup)

old_condition = "        if escalation_count < 3:\n"
new_condition = "        if escalation_count < 1:\n"

old_pending = '''        # Request 3: start ticket collection, using the issue already given.
        pending_ticket = {
'''
new_pending = '''        # Start human-support ticket collection immediately after an explicit request.
        # A customer does not have to disclose the issue before requesting a human.
        if not complaint:
            complaint = (
                "Customer requested to speak with a human support representative; "
                "issue description not provided."
            )

        pending_ticket = {
'''

old_cancel = '''        "leave it",
'''
new_cancel = '''        "leave it",
        "do not need human support",
        "do not want human support",
        "i do not need human support",
        "i do not want human support",
        "no human support needed",
        "no ticket generation",
        "ticket generation is not needed",
        "ticket generation is not required",
        "no ticket is needed",
        "no ticket needed",
        "no ticket required",
        "i do not need a support request",
'''

checks = [
    (old_condition, new_condition, "human escalation threshold"),
    (old_pending, new_pending, "human ticket fallback"),
    (old_cancel, new_cancel, "cancellation phrases"),
]

for old, new, label in checks:
    count = source.count(old)
    if count != 1:
        raise SystemExit(
            f"STOP: Expected exactly one match for {label}, found {count}. "
            f"No changes were written."
        )
    source = source.replace(old, new, 1)

path.write_text(source, encoding="utf-8")
print("Patch applied successfully.")
print(f"Backup saved as: {backup}")

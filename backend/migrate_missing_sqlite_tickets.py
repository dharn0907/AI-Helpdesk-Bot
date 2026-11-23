from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine, text
from database.database import SessionLocal
from database.models import Ticket

BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / "helpdesk.db"

source_engine = create_engine(
    f"sqlite:///{SQLITE_PATH.as_posix()}"
)

def convert_datetime(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

def migrate():
    source = source_engine.connect()
    target = SessionLocal()

    migrated = 0
    skipped = 0

    try:
        rows = source.execute(text("""
            SELECT ticket_id, session_id, customer_message,
                   additional_details, customer_email, intent,
                   priority, status, agent_reply,
                   created_at, updated_at
            FROM tickets
            ORDER BY id
        """)).mappings().all()

        existing_ids = {
            row[0] for row in target.query(Ticket.ticket_id).all()
        }

        print(f"SQLite tickets found: {len(rows)}")
        print(f"Existing Supabase tickets: {len(existing_ids)}")

        for row in rows:

            if row["ticket_id"] in existing_ids:
                print(f"Skipping duplicate: {row['ticket_id']}")
                skipped += 1
                continue

            new_ticket = Ticket(
                ticket_id=row["ticket_id"],
                session_id=row["session_id"],
                customer_message=row["customer_message"],
                additional_details=row["additional_details"],
                customer_email=row["customer_email"],
                intent=row["intent"],
                priority=row["priority"],
                status=row["status"],
                agent_reply=row["agent_reply"],
                created_at=convert_datetime(row["created_at"]),
                updated_at=convert_datetime(row["updated_at"]),
            )

            target.add(new_ticket)
            existing_ids.add(row["ticket_id"])
            migrated += 1

        target.commit()

        print("\n===== MIGRATION COMPLETE =====")
        print(f"Imported: {migrated}")
        print(f"Skipped: {skipped}")
        print(f"Total Supabase tickets: {target.query(Ticket).count()}")

    except Exception as e:
        target.rollback()
        print("Migration failed. Changes rolled back.")
        raise e

    finally:
        source.close()
        target.close()
        source_engine.dispose()

if __name__ == "__main__":
    migrate()

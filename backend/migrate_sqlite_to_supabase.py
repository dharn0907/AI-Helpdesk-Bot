
"""Safely migrate existing SQLite tickets to Supabase PostgreSQL."""

from pathlib import Path

from sqlalchemy import create_engine, text, or_
from sqlalchemy.orm import sessionmaker

from database.database import SessionLocal
from database.models import Ticket


# Original SQLite database
BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / "helpdesk.db"

if not SQLITE_PATH.exists():
    raise FileNotFoundError(f"SQLite database not found: {SQLITE_PATH}")

sqlite_engine = create_engine(
    f"sqlite:///{SQLITE_PATH.as_posix()}",
    connect_args={"check_same_thread": False}
)

SQLiteSession = sessionmaker(bind=sqlite_engine)


def migrate():
    source = SQLiteSession()
    target = SessionLocal()

    migrated = 0
    skipped = 0

    try:
        old_tickets = source.query(Ticket).order_by(Ticket.id).all()

        print(f"Found {len(old_tickets)} tickets in SQLite.")

        for old in old_tickets:
            existing = (
                target.query(Ticket)
                .filter(
                    or_(
                        Ticket.id == old.id,
                        Ticket.ticket_id == old.ticket_id
                    )
                )
                .first()
            )

            if existing:
                print(f"Skipping existing ticket: {old.ticket_id}")
                skipped += 1
                continue

            new_ticket = Ticket(
                id=old.id,
                ticket_id=old.ticket_id,
                session_id=old.session_id,
                customer_message=old.customer_message,
                additional_details=old.additional_details,
                customer_email=old.customer_email,
                intent=old.intent,
                priority=old.priority,
                status=old.status,
                agent_reply=old.agent_reply,
                created_at=old.created_at,
                updated_at=old.updated_at,
            )

            target.add(new_ticket)
            migrated += 1

        target.commit()

        # Keep PostgreSQL's auto-generated ID sequence in sync.
        target.execute(text("""
            SELECT setval(
                pg_get_serial_sequence('tickets', 'id'),
                COALESCE((SELECT MAX(id) FROM tickets), 1),
                true
            )
        """))
        target.commit()

        print("\nMigration completed successfully!")
        print(f"New tickets migrated: {migrated}")
        print(f"Existing tickets skipped: {skipped}")
        print(f"Total tickets in Supabase: {target.query(Ticket).count()}")

    except Exception:
        target.rollback()
        raise

    finally:
        source.close()
        target.close()
        sqlite_engine.dispose()


if __name__ == "__main__":
    migrate()

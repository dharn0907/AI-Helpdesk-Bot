from database.database import SessionLocal
from database.models import Ticket

db = SessionLocal()

try:
    tickets = (
        db.query(Ticket)
        .filter(Ticket.status.in_(["Resolved", "Closed"]))
        .order_by(Ticket.id.desc())
        .all()
    )

    for ticket in tickets:
        print("\n" + "=" * 60)
        print("Ticket:", ticket.ticket_id)
        print("Intent:", ticket.intent)
        print("Status:", ticket.status)
        print("\nCustomer complaint:")
        print(ticket.customer_message)
        print("\nAgent solution:")
        print(ticket.agent_reply or "No agent reply recorded")

finally:
    db.close()

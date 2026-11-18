from database.database import SessionLocal
from database.models import Ticket

ticket_ids = ["TKT-9E9155F4", "TKT-CEFF824B"]

db = SessionLocal()

try:
    for ticket_id in ticket_ids:
        ticket = db.query(Ticket).filter(
            Ticket.ticket_id == ticket_id
        ).first()

        print("\n" + "=" * 55)
        print("Ticket:", ticket_id)

        if not ticket:
            print("Not found")
            continue

        print("Status:", ticket.status)
        print("Agent reply saved:", bool(ticket.agent_reply))
        print("Agent reply:", ticket.agent_reply)

finally:
    db.close()

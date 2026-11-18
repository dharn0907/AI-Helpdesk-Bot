from sqlalchemy import func
from database.database import SessionLocal
from database.models import Ticket, Company

db = SessionLocal()

try:
    print("Total tickets:", db.query(func.count(Ticket.id)).scalar())
    print("\nTickets by status:")

    results = (
        db.query(Ticket.status, func.count(Ticket.id))
        .group_by(Ticket.status)
        .all()
    )

    for status, count in results:
        print(status, ":", count)

    print("\nCompanies:")
    for company in db.query(Company).all():
        print(company.id, company.name, "Active:", company.is_active)

    print("\nRecent ticket metadata (no customer details):")
    tickets = (
        db.query(Ticket)
        .order_by(Ticket.id.desc())
        .limit(10)
        .all()
    )

    for ticket in tickets:
        print(
            ticket.id,
            ticket.ticket_id,
            "| Intent:", ticket.intent,
            "| Status:", ticket.status,
            "| Has agent reply:", bool(ticket.agent_reply)
        )

finally:
    db.close()

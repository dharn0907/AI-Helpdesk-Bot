from database.database import SessionLocal
from database.models import Company, TicketResolutionReview

db = SessionLocal()

try:
    company = db.query(Company).filter(
        Company.is_active.is_(True)
    ).first()

    print("COMPANY:", company.id if company else None)

    if company:
        records = db.query(TicketResolutionReview).filter(
            TicketResolutionReview.company_id == company.id,
            TicketResolutionReview.approval_status == "approved"
        ).all()

        for r in records:
            print("=" * 60)
            print("Ticket:", r.ticket_id)
            print("Intent:", r.intent)
            print("Complaint:", r.complaint)
            print("Solution:", (r.approved_solution or "")[:150])

        print("\nTOTAL APPROVED:", len(records))

finally:
    db.close()

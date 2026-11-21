from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Company, Ticket, TicketResolutionReview

router = APIRouter(
    prefix="/historical-solutions",
    tags=["Historical Solutions"]
)


def get_active_company(db: Session):
    company = db.query(Company).filter(
        Company.is_active.is_(True)
    ).order_by(Company.id.asc()).first()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="No active company found."
        )

    return company


@router.get("/")
def get_historical_solutions(db: Session = Depends(get_db)):
    company = get_active_company(db)

    reviews = (
        db.query(TicketResolutionReview, Ticket)
        .join(
            Ticket,
            Ticket.ticket_id == TicketResolutionReview.ticket_id
        )
        .filter(
            TicketResolutionReview.company_id == company.id,
            TicketResolutionReview.approval_status == "approved",
            TicketResolutionReview.approved_solution.isnot(None),
            TicketResolutionReview.approved_solution != ""
        )
        .order_by(TicketResolutionReview.approved_at.desc())
        .all()
    )

    results = []

    for review, ticket in reviews:
        results.append({
            "ticket_id": review.ticket_id,
            "complaint": review.complaint or ticket.customer_message,
            "intent": review.intent or ticket.intent,
            "approved_solution": review.approved_solution,
            "approval_status": review.approval_status,
            "approved_at": review.approved_at,
            "customer_email": ticket.customer_email,
            "session_id": ticket.session_id,
            "ticket_status": ticket.status
        })

    return {
        "total": len(results),
        "solutions": results
    }


@router.patch("/{ticket_id}")
def update_historical_solution(
    ticket_id: str,
    data: dict,
    db: Session = Depends(get_db)
):
    company = get_active_company(db)

    review = db.query(TicketResolutionReview).filter(
        TicketResolutionReview.ticket_id == ticket_id,
        TicketResolutionReview.company_id == company.id,
        TicketResolutionReview.approval_status == "approved"
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Approved historical solution not found."
        )

    solution = str(
        data.get("approved_solution", "")
    ).strip()

    if not solution:
        raise HTTPException(
            status_code=400,
            detail="Solution cannot be empty."
        )

    review.approved_solution = solution

    db.commit()
    db.refresh(review)

    return {
        "message": "Historical solution updated successfully.",
        "ticket_id": review.ticket_id,
        "approved_solution": review.approved_solution
    }


@router.delete("/{ticket_id}")
def delete_historical_solution(
    ticket_id: str,
    db: Session = Depends(get_db)
):
    company = get_active_company(db)

    review = db.query(TicketResolutionReview).filter(
        TicketResolutionReview.ticket_id == ticket_id,
        TicketResolutionReview.company_id == company.id,
        TicketResolutionReview.approval_status == "approved"
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Approved historical solution not found."
        )

    db.delete(review)
    db.commit()

    return {
        "message": "Historical solution deleted successfully.",
        "ticket_id": ticket_id
    }
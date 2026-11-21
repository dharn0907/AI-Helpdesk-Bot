from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.database import get_db
from database.models import Company, HistoricalSolutionAttempt

router = APIRouter(
    prefix="/historical-solution-attempts",
    tags=["Historical Solution Attempts"]
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
def get_historical_solution_attempts(
    status: str = None,
    search: str = None,
    db: Session = Depends(get_db)
):
    company = get_active_company(db)

    query = db.query(HistoricalSolutionAttempt).filter(
        HistoricalSolutionAttempt.company_id == company.id
    )

    # Filter by attempt status
    if status and status != "all":
        query = query.filter(
            HistoricalSolutionAttempt.attempt_status == status
        )

    # Search complaints, matched tickets, customer emails,
    # and created ticket IDs.
    if search and search.strip():
        search_term = f"%{search.strip()}%"

        query = query.filter(
            or_(
                HistoricalSolutionAttempt.customer_complaint.ilike(search_term),
                HistoricalSolutionAttempt.matched_ticket_id.ilike(search_term),
                HistoricalSolutionAttempt.customer_email.ilike(search_term),
                HistoricalSolutionAttempt.created_ticket_id.ilike(search_term),
                HistoricalSolutionAttempt.retrieved_solution.ilike(search_term),
            )
        )

    attempts = query.order_by(
        HistoricalSolutionAttempt.created_at.desc()
    ).all()

    results = []

    for attempt in attempts:
        results.append({
            "id": attempt.id,
            "session_id": attempt.session_id,
            "customer_email": attempt.customer_email,
            "customer_complaint": attempt.customer_complaint,
            "matched_ticket_id": attempt.matched_ticket_id,
            "retrieved_solution": attempt.retrieved_solution,
            "similarity_score": attempt.similarity_score,
            "response_delivered": attempt.response_delivered,
            "resolution_confirmation": attempt.resolution_confirmation,
            "attempt_status": attempt.attempt_status,
            "created_ticket_id": attempt.created_ticket_id,
            "created_at": attempt.created_at,
            "updated_at": attempt.updated_at,
        })

    return {
        "total": len(results),
        "attempts": results
    }
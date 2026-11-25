from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.database import get_db
from services.workspace_auth import get_workspace_company
from database.models import (
    Company,
    HistoricalSolutionAttempt,
    OrganizationMember,
)

router = APIRouter(
    prefix="/historical-solution-attempts",
    tags=["Historical Solution Attempts"]
)


def get_agent_company(db, email, company_id):
    email = str(email or "").strip().lower()

    if not email or not company_id:
        raise HTTPException(401, "Agent email or company ID is missing.")

    member = db.query(OrganizationMember).filter(
        OrganizationMember.email == email,
        OrganizationMember.organization_id == company_id,
        OrganizationMember.role == "support_agent",
        OrganizationMember.status == "approved",
    ).first()

    if not member:
        raise HTTPException(401, "Approved agent membership not found for this company.")

    return {"id": member.organization_id}


def get_request_company(db, authorization, x_company_id, agent_email):
    if agent_email:
        return get_agent_company(db, agent_email, x_company_id)

    return get_workspace_company(authorization, x_company_id, db)


@router.get("/")
def get_historical_solution_attempts(
    status: str = None,
    search: str = None,
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
    agent_email: str = Header(default=None, alias="X-Agent-Email"),
):
    company = get_request_company(
        db, authorization, x_company_id, agent_email
    )

    query = db.query(HistoricalSolutionAttempt).filter(
        HistoricalSolutionAttempt.company_id == company["id"]
    )

    if status and status != "all":
        query = query.filter(
            HistoricalSolutionAttempt.attempt_status == status
        )

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

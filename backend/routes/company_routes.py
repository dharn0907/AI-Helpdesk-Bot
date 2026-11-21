
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Company
from services.company_service import (
    create_company,
    get_bot_configuration,
    update_bot_configuration,
)


router = APIRouter(
    prefix="/companies",
    tags=["Company and Bot Configuration"],
)






@router.get("/current")
def get_current_company(
    db: Session = Depends(get_db),
):
    """Return the single active company and its bot configuration."""

    company = db.query(Company).filter(
        Company.is_active.is_(True)
    ).first()

    if not company:
        return {
            "exists": False,
            "message": "No company has been registered yet.",
        }

    configuration = get_bot_configuration(db, company.id)

    return {
        "exists": True,
        "company_id": company.id,
        "company_name": company.name,
        "slug": company.slug,
        "historical_solution_timeout": {
            "enabled": company.historical_solution_timeout_enabled,
            "timeout_hours": company.historical_solution_timeout_hours,
        }, 

        "configuration": {
            "bot_name": configuration.bot_name if configuration else "Support Assistant",
            "what_this_bot_helps_with": configuration.what_this_bot_helps_with if configuration else "",
            "about_business": configuration.about_business if configuration else "",
            "how_to_respond": configuration.how_to_respond if configuration else "",
            "when_to_handoff": configuration.when_to_handoff if configuration else "",
            "dos": configuration.dos if configuration else "",
            "donts": configuration.donts if configuration else "",
            "advanced_instructions": configuration.advanced_instructions if configuration else "",
        },
    }


@router.post("/")
def register_company(
    data: dict,
    db: Session = Depends(get_db),
):
    try:
        company = create_company(
            db=db,
            name=data.get("name"),
            slug=data.get("slug"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return {
        "message": "Company registered successfully.",
        "company_id": company.id,
        "company_name": company.name,
        "slug": company.slug,
        "bot_public_id": company.bot_public_id,
    }


@router.patch("/{company_id}/configuration")
def update_company_bot_configuration(
    company_id: int,
    data: dict,
    db: Session = Depends(get_db),
):
    try:
        configuration = update_bot_configuration(
            db=db,
            company_id=company_id,
            updates=data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message": "Bot configuration updated successfully.",
        "company_id": company_id,
        "configuration": {
            "bot_name": configuration.bot_name,
            "what_this_bot_helps_with": configuration.what_this_bot_helps_with,
            "about_business": configuration.about_business,
            "how_to_respond": configuration.how_to_respond,
            "when_to_handoff": configuration.when_to_handoff,
            "dos": configuration.dos,
            "donts": configuration.donts,
            "advanced_instructions": configuration.advanced_instructions,
        },
    }
@router.patch("/current/historical-solution-timeout")
def update_historical_solution_timeout(
    data: dict,
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(
        Company.is_active.is_(True)
    ).first()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="No active company found.",
        )

    enabled = data.get("enabled")
    timeout_hours = data.get("timeout_hours")

    if not isinstance(enabled, bool):
        raise HTTPException(
            status_code=400,
            detail="'enabled' must be true or false.",
        )

    if timeout_hours is not None:
        try:
            timeout_hours = int(timeout_hours)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Timeout hours must be a valid integer.",
            )

        if timeout_hours < 1 or timeout_hours > 168:
            raise HTTPException(
                status_code=400,
                detail="Timeout must be between 1 and 168 hours.",
            )

    company.historical_solution_timeout_enabled = enabled

    if timeout_hours is not None:
        company.historical_solution_timeout_hours = timeout_hours

    db.commit()
    db.refresh(company)

    return {
        "message": "Historical solution timeout settings updated.",
        "enabled": company.historical_solution_timeout_enabled,
        "timeout_hours": company.historical_solution_timeout_hours,
    }

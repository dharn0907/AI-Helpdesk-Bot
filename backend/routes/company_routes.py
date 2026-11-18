
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

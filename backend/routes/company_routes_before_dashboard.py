import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from services.company_service import (
    create_company,
    update_bot_configuration,
)


router = APIRouter(
    prefix="/companies",
    tags=["Company and Bot Configuration"],
)


def require_admin_key(
    x_admin_api_key: str = Header(default=None, alias="X-Admin-API-Key"),
):
    configured_key = os.getenv("ADMIN_API_KEY")

    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="Company administration is not configured.",
        )

    if not x_admin_api_key or not secrets.compare_digest(
        x_admin_api_key,
        configured_key,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing administrator credentials.",
        )

    return True


@router.post("/")
def register_company(
    data: dict,
    authorized: bool = Depends(require_admin_key),
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
    authorized: bool = Depends(require_admin_key),
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

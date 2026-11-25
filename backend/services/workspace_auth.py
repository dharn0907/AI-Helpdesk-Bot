import os
import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException
from sqlalchemy import text

load_dotenv()

def get_workspace_company(authorization, company_id, db):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please log in.")

    try:
        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
            raise ValueError("JWT secret missing")

        payload = jwt.decode(
            authorization.split(" ", 1)[1],
            secret,
            algorithms=["HS256"]
        )

        if payload.get("type") != "user":
            raise ValueError("Invalid token")

        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Invalid or expired session.")

    if not company_id:
        raise HTTPException(400, "Select a company.")

    company = db.execute(text("""
        SELECT c.id, c.name, c.slug
        FROM companies c
        JOIN company_memberships m ON m.company_id = c.id
        WHERE m.user_id = :uid
          AND c.id = :cid
          AND c.is_active IS TRUE
    """), {"uid": user_id, "cid": company_id}).mappings().first()

    if not company:
        raise HTTPException(403, "You do not have access to this company.")

    return company

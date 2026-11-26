
from fastapi import APIRouter, Depends, Header, HTTPException, Header
from sqlalchemy import text

import jwt
import hashlib
import hmac
from dotenv import load_dotenv
from services.email_service import send_company_otp

from datetime import datetime, timedelta, timezone
import hashlib
import os
import re
import secrets
from sqlalchemy.orm import Session
from services.company_smtp_service import encrypt_password, test_company_smtp

from database.database import get_db
from services.workspace_auth import get_workspace_company, get_deletion_actor, record_deletion
from database.models import Company, CompanyEmailVerification, Chatbot, OrganizationSettings, SupportEmailVerification, TicketConversationSettings
from services.email_service import send_verification_email
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
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias='X-Company-ID')
):
    """Return the single active company and its bot configuration."""

    company = get_workspace_company(authorization, x_company_id, db)

    if not company:
        return {
            "exists": False,
            "message": "No company has been registered yet.",
        }

    configuration = get_bot_configuration(db, company['id'])

    return {
        "exists": True,
        "company_id": company['id'],
        "company_name": company['name'],
        "slug": company['slug'],
        "historical_solution_timeout": {
            "enabled": db.query(Company).filter(Company.id == company['id']).first().historical_solution_timeout_enabled,
            "timeout_hours": db.query(Company).filter(Company.id == company['id']).first().historical_solution_timeout_hours,
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
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Company name is required.")

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid company email is required.")

    # Generate the same normalized slug for checking existing companies.
    raw_slug = str(data.get("slug") or name).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw_slug).strip("-")

    if not slug:
        raise HTTPException(status_code=400, detail="A valid company slug is required.")

    # Reuse an existing inactive company when retrying verification.
    company = db.query(Company).filter(Company.slug == slug).first()

    if company:
        if company.is_active:
            raise HTTPException(
                status_code=409,
                detail="This company is already registered and active."
            )

        previous = (
            db.query(CompanyEmailVerification)
            .filter(CompanyEmailVerification.company_id == company.id)
            .first()
        )

        if previous and previous.email.lower() != email:
            raise HTTPException(
                status_code=409,
                detail="This pending registration uses a different email address."
            )

        # Replace the old verification request, keeping the company and bot.
        db.query(CompanyEmailVerification).filter(
            CompanyEmailVerification.company_id == company.id
        ).delete(synchronize_session=False)

    else:
        try:
            company = create_company(
                db=db,
                name=name,
                slug=slug,
                is_active=False,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    verification = CompanyEmailVerification(
        company_id=company.id,
        email=email,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    try:
        db.add(verification)
        db.commit()
        db.refresh(company)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create verification request."
        )

    backend_url = os.getenv(
        "BACKEND_PUBLIC_URL",
        "http://127.0.0.1:8000"
    ).rstrip("/")

    verification_url = (
        f"{backend_url}/companies/verify-email?token={raw_token}"
    )

    sent, message = send_verification_email(email, verification_url)

    if not sent:
        # Keep the company inactive and the verification request.
        # Submitting registration again will generate a fresh token.
        raise HTTPException(
            status_code=503,
            detail="Email delivery failed. Submit registration again to retry."
        )

    return {
        "message": "Verification email sent. Check your inbox to activate your company.",
        "company_id": company.id,
        "company_name": company.name,
        "email": email,
    }


@router.get("/verify-email")
def verify_company_email(
    token: str,
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    verification = db.query(CompanyEmailVerification).filter(
        CompanyEmailVerification.token_hash == token_hash,
        CompanyEmailVerification.verified_at.is_(None),
    ).first()

    if not verification:
        raise HTTPException(status_code=400, detail="Invalid or already-used verification link.")

    now = datetime.now(timezone.utc)
    expires_at = verification.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(status_code=400, detail="Verification link has expired.")

    company = db.query(Company).filter(
        Company.id == verification.company_id
    ).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    company.is_active = True
    verification.verified_at = now
    db.commit()

    return {
        "message": "Company email verified successfully. Your company is now active.",
        "company_id": company.id,
        "company_name": company.name,
    }


@router.patch("/{company_id}/configuration")
def update_company_bot_configuration(
    company_id: int,
    data: dict,
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias='X-Company-ID')
):
    company = get_workspace_company(authorization, x_company_id, db)
    if company_id != company['id']:
        raise HTTPException(status_code=403, detail='Company access denied.')

    company = get_workspace_company(authorization, x_company_id, db)
    if company_id != company['id']:
        raise HTTPException(status_code=403, detail='Company access denied.')

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
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias='X-Company-ID')
):
    workspace_company = get_workspace_company(authorization, x_company_id, db)
    company = db.query(Company).filter(Company.id == workspace_company['id']).first()

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



@router.get("/current/ticket-conversation-timeout")
def get_ticket_conversation_timeout(
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    workspace_company = get_workspace_company(authorization, x_company_id, db)
    if not workspace_company:
        raise HTTPException(status_code=404, detail="Company not found.")
    settings = db.query(TicketConversationSettings).filter(
        TicketConversationSettings.company_id == workspace_company["id"]
    ).first()
    return {
        "enabled": settings.enabled if settings else True,
        "timeout_minutes": settings.timeout_minutes if settings else 2,
    }


@router.patch("/current/ticket-conversation-timeout")
def update_ticket_conversation_timeout(
    data: dict,
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    workspace_company = get_workspace_company(authorization, x_company_id, db)
    if not workspace_company:
        raise HTTPException(status_code=404, detail="Company not found.")

    enabled = data.get("enabled", True)
    timeout_minutes = data.get("timeout_minutes", 2)
    if not isinstance(enabled, bool):
        raise HTTPException(status_code=400, detail="'enabled' must be true or false.")
    if isinstance(timeout_minutes, bool) or not isinstance(timeout_minutes, int) or not 1 <= timeout_minutes <= 30:
        raise HTTPException(status_code=400, detail="Ticket conversation timeout must be between 1 and 30 minutes.")

    settings = db.query(TicketConversationSettings).filter(
        TicketConversationSettings.company_id == workspace_company["id"]
    ).first()
    if not settings:
        settings = TicketConversationSettings(company_id=workspace_company["id"])
        db.add(settings)
    settings.enabled = enabled
    settings.timeout_minutes = timeout_minutes
    db.commit()
    db.refresh(settings)
    return {
        "message": "Ticket conversation inactivity settings updated.",
        "enabled": settings.enabled,
        "timeout_minutes": settings.timeout_minutes,
    }


@router.get("/current/chatbots")
def list_company_chatbots(db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias='X-Company-ID')
):
    company = get_workspace_company(authorization, x_company_id, db)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    bots = db.query(Chatbot).filter(
        Chatbot.organization_id == company['id'],
        Chatbot.status != "inactive"
    ).order_by(Chatbot.id.desc()).all()

    return [{
        "id": bot.id,
        "public_id": str(bot.public_id),
        "bot_name": bot.bot_name,
        "description": bot.description,
        "status": bot.status
    } for bot in bots]


@router.post("/current/chatbots")
def create_company_chatbot(data: dict, db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias='X-Company-ID')
):
    company = get_workspace_company(authorization, x_company_id, db)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    name = str(data.get("bot_name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Chatbot name is required")

    bot = Chatbot(
        organization_id=company['id'],
        bot_name=name,
        description=str(data.get("description") or "").strip() or None,
        status="active"
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)

    return {
        "id": bot.id,
        "public_id": str(bot.public_id),
        "bot_name": bot.bot_name,
        "description": bot.description,
        "status": bot.status
    }


@router.patch("/current/chatbots/{chatbot_id}")
def update_company_chatbot(chatbot_id: int, data: dict, db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias='X-Company-ID')
):
    company = get_workspace_company(authorization, x_company_id, db)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    bot = db.query(Chatbot).filter(
        Chatbot.id == chatbot_id,
        Chatbot.organization_id == company['id']
    ).first()

    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    if "bot_name" in data:
        name = str(data["bot_name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Chatbot name cannot be empty")
        bot.bot_name = name

    if "description" in data:
        bot.description = str(data["description"] or "").strip() or None

    if "status" in data and data["status"] in ("active", "inactive"):
        bot.status = data["status"]

    db.commit()
    db.refresh(bot)

    return {
        "id": bot.id,
        "public_id": str(bot.public_id),
        "bot_name": bot.bot_name,
        "description": bot.description,
        "status": bot.status
    }


@router.delete("/current/chatbots/{chatbot_id}")
def delete_company_chatbot(chatbot_id: int, db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias='X-Company-ID')
):
    company = get_workspace_company(authorization, x_company_id, db)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    bot = db.query(Chatbot).filter(
        Chatbot.id == chatbot_id,
        Chatbot.organization_id == company['id']
    ).first()

    if not bot:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    if bot.status != "inactive":
        actor_id = get_deletion_actor(authorization)
        record_deletion(
            db, "chatbot", bot.id, bot.bot_name,
            company["id"], actor_id, "deactivated"
        )
        bot.status = "inactive"
        db.commit()
    return {"success": True, "message": "Chatbot deactivated and recorded"}


# ============================================================
# COMPANY ACCOUNT AUTHENTICATION
# ============================================================

load_dotenv()

def _password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 310000
    ).hex()
    return f"{salt}${digest}"


def _password_valid(password, stored):
    try:
        salt, expected = stored.split("$", 1)
        actual = _password_hash(password, salt).split("$", 1)[1]
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _make_company_token(company):
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=500, detail="JWT secret is not configured.")
    return jwt.encode(
        {
            "company_id": company['id'],
            "email": company.email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        },
        secret,
        algorithm="HS256",
    )


@router.post("/signup")
def company_signup(data: dict, db: Session = Depends(get_db)):
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if len(name) < 2:
        raise HTTPException(400, "Enter a valid company name.")
    if "@" not in email or len(email) > 320:
        raise HTTPException(400, "Enter a valid company email.")
    if len(password) < 8:
        raise HTTPException(400, "Password must contain at least 8 characters.")

    existing = db.query(Company).filter(Company.email.ilike(email)).first()
    if existing:
        raise HTTPException(409, "This email is already registered.")

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise HTTPException(400, "Company name cannot be used.")

    if db.query(Company).filter(Company.slug == slug).first():
        slug = f"{slug}-{secrets.token_hex(3)}"

    try:
        company = create_company(
            db=db, name=name, slug=slug, is_active=False
        )
        company.email = email
        company.password_hash = _password_hash(password)
        db.commit()
        db.refresh(company)

        otp = f"{secrets.randbelow(1000000):06d}"
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()

        db.execute(text("""
            DELETE FROM company_login_otps WHERE company_id = :cid
        """), {"cid": company.id})

        db.execute(text("""
            INSERT INTO company_login_otps
                (company_id, otp_hash, expires_at, created_at)
            VALUES
                (:cid, :otp, :expires, :created)
        """), {
            "cid": company.id,
            "otp": otp_hash,
            "expires": datetime.now(timezone.utc) + timedelta(minutes=10),
            "created": datetime.now(timezone.utc),
        })
        db.commit()

        sent, _ = send_company_otp(email, otp)
        if not sent:
            raise HTTPException(503, "Could not send OTP. Check SMTP settings.")

        return {
            "message": "Verification code sent to your company email.",
            "company_id": company.id,
            "email": email,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, "Company registration failed.")


@router.post("/verify-otp")
def verify_company_otp(data: dict, db: Session = Depends(get_db)):
    email = str(data.get("email") or "").strip().lower()
    otp = str(data.get("otp") or "").strip()

    if len(otp) != 6 or not otp.isdigit():
        raise HTTPException(400, "Enter the 6-digit verification code.")

    company = db.query(Company).filter(
        Company.email.ilike(email)
    ).first()

    if not company:
        raise HTTPException(404, "Company account not found.")

    record = db.execute(text("""
        SELECT otp_hash, expires_at
        FROM company_login_otps
        WHERE company_id = :cid
    """), {"cid": company.id}).mappings().first()

    if not record:
        raise HTTPException(400, "No active OTP. Please register again.")

    expiry = record["expires_at"]
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    supplied_hash = hashlib.sha256(otp.encode()).hexdigest()
    if expiry < datetime.now(timezone.utc) or not hmac.compare_digest(
        supplied_hash, record["otp_hash"]
    ):
        raise HTTPException(400, "Invalid or expired verification code.")

    company.is_active = True
    db.execute(text("""
        DELETE FROM company_login_otps WHERE company_id = :cid
    """), {"cid": company.id})
    db.commit()

    return {
        "message": "Company email verified. You can now log in.",
        "company_id": company.id,
        "email": company.email,
    }


@router.post("/login")
def company_login(data: dict, db: Session = Depends(get_db)):
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    company = db.query(Company).filter(
        Company.email.ilike(email)
    ).first()

    if not company or not company.password_hash:
        raise HTTPException(401, "Invalid email or password.")

    if not _password_valid(password, company.password_hash):
        raise HTTPException(401, "Invalid email or password.")

    if not company.is_active:
        raise HTTPException(403, "Verify your company email before logging in.")

    return {
        "access_token": _make_company_token(company),
        "token_type": "bearer",
        "company": {
            "id": company.id,
            "name": company.name,
            "email": company.email,
            "slug": company.slug,
        },
    }


@router.get("/me")
def company_me(
    authorization: str = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authentication required.")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET_KEY"),
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired login session.")

    company = db.query(Company).filter(
        Company.id == payload.get("company_id"),
        Company.is_active.is_(True),
    ).first()

    if not company:
        raise HTTPException(401, "Company account is unavailable.")

    return {
        "id": company.id,
        "name": company.name,
        "email": company.email,
        "slug": company.slug,
    }


# ============================================================
# MULTI-COMPANY USER AUTHENTICATION (EMAIL OTP)
# ============================================================

import os as _mu_os
import re as _mu_re
import hmac as _mu_hmac
import hashlib as _mu_hashlib
import secrets as _mu_secrets
import jwt as _mu_jwt

from datetime import datetime as _mu_datetime
from datetime import timedelta as _mu_timedelta
from datetime import timezone as _mu_timezone
from sqlalchemy import text as _mu_text
from fastapi import Header as _mu_Header


def _mu_setup(db):
    db.execute(_mu_text("""
        CREATE TABLE IF NOT EXISTS app_users (
            id BIGSERIAL PRIMARY KEY,
            email VARCHAR(320) NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.execute(_mu_text("""
        CREATE TABLE IF NOT EXISTS app_user_otps (
            email VARCHAR(320) PRIMARY KEY,
            otp_hash VARCHAR(64) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.execute(_mu_text("""
        CREATE TABLE IF NOT EXISTS company_memberships (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, company_id)
        )
    """))
    db.commit()


def _mu_secret():
    from dotenv import load_dotenv
    load_dotenv()
    secret = _mu_os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise HTTPException(500, "JWT_SECRET_KEY is not configured.")
    return secret


def _mu_create_token(user):
    return _mu_jwt.encode({
        "sub": str(user["id"]),
        "email": user["email"],
        "exp": _mu_datetime.now(_mu_timezone.utc) + _mu_timedelta(hours=12),
        "type": "user"
    }, _mu_secret(), algorithm="HS256")


def _mu_get_user(authorization, db):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please verify your email first.")
    token = authorization.split(" ", 1)[1]
    try:
        payload = _mu_jwt.decode(token, _mu_secret(), algorithms=["HS256"])
        if payload.get("type") != "user":
            raise ValueError("Wrong token type")
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Your session expired. Please verify your email again.")

    user = db.execute(_mu_text("""
        SELECT id, email FROM app_users WHERE id = :uid
    """), {"uid": user_id}).mappings().first()

    if not user:
        raise HTTPException(401, "User account not found.")
    return user


@router.post("/auth/request-otp")
def multiuser_request_otp(data: dict, db: Session = Depends(get_db)):
    _mu_setup(db)
    email = str(data.get("email") or "").strip().lower()

    if not _mu_re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "Enter a valid email address.")

    otp = f"{_mu_secrets.randbelow(1000000):06d}"
    otp_hash = _mu_hashlib.sha256(otp.encode()).hexdigest()

    db.execute(_mu_text("""
        INSERT INTO app_user_otps (email, otp_hash, expires_at, created_at)
        VALUES (:email, :hash, :expires, NOW())
        ON CONFLICT (email) DO UPDATE SET
            otp_hash = EXCLUDED.otp_hash,
            expires_at = EXCLUDED.expires_at,
            created_at = NOW()
    """), {
        "email": email,
        "hash": otp_hash,
        "expires": _mu_datetime.now(_mu_timezone.utc) + _mu_timedelta(minutes=10)
    })
    db.commit()

    sent, _ = send_company_otp(email, otp)
    if not sent:
        raise HTTPException(503, "Could not send OTP. Please try again.")

    return {"message": "OTP sent successfully.", "email": email}


@router.post("/auth/verify-otp")
def multiuser_verify_otp(data: dict, db: Session = Depends(get_db)):
    _mu_setup(db)
    email = str(data.get("email") or "").strip().lower()
    otp = str(data.get("otp") or "").strip()

    if len(otp) != 6 or not otp.isdigit():
        raise HTTPException(400, "Enter the 6-digit OTP.")

    record = db.execute(_mu_text("""
        SELECT otp_hash, expires_at
        FROM app_user_otps WHERE email = :email
    """), {"email": email}).mappings().first()

    if not record:
        raise HTTPException(400, "No active OTP. Request a new code.")

    expiry = record["expires_at"]
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=_mu_timezone.utc)

    supplied = _mu_hashlib.sha256(otp.encode()).hexdigest()
    if expiry < _mu_datetime.now(_mu_timezone.utc) or not _mu_hmac.compare_digest(
        supplied, record["otp_hash"]
    ):
        raise HTTPException(400, "Invalid or expired OTP.")

    db.execute(_mu_text("""
        INSERT INTO app_users (email)
        VALUES (:email)
        ON CONFLICT (email) DO NOTHING
    """), {"email": email})

    user = db.execute(_mu_text("""
        SELECT id, email FROM app_users WHERE email = :email
    """), {"email": email}).mappings().first()

    db.execute(_mu_text("""
        DELETE FROM app_user_otps WHERE email = :email
    """), {"email": email})
    db.commit()

    return {
        "message": "Email verified.",
        "access_token": _mu_create_token(user),
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"]}
    }


@router.get("/auth/companies")
def multiuser_list_companies(
    authorization: str = _mu_Header(default=None),
    db: Session = Depends(get_db)
):
    _mu_setup(db)
    user = _mu_get_user(authorization, db)

    rows = db.execute(_mu_text("""
        SELECT c.id, c.name, c.slug
        FROM companies c
        JOIN company_memberships m ON m.company_id = c.id
        WHERE m.user_id = :uid
        ORDER BY c.name
    """), {"uid": user["id"]}).mappings().all()

    return {
        "email": user["email"],
        "companies": [dict(row) for row in rows]
    }


@router.post("/auth/companies")
def multiuser_create_company(
    data: dict,
    authorization: str = _mu_Header(default=None),
    db: Session = Depends(get_db)
):
    _mu_setup(db)
    db.execute(_mu_text("""
        ALTER TABLE companies
        ADD COLUMN IF NOT EXISTS owner_user_id BIGINT
    """))
    db.execute(_mu_text("""
        UPDATE companies c
        SET owner_user_id = (
            SELECT m.user_id FROM company_memberships m
            WHERE m.company_id = c.id
            ORDER BY m.created_at ASC, m.id ASC
            LIMIT 1
        )
        WHERE c.owner_user_id IS NULL
    """))
    user = _mu_get_user(authorization, db)
    name = str(data.get("name") or "").strip()

    if len(name) < 2:
        raise HTTPException(400, "Enter a valid company name.")

    slug = _mu_re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise HTTPException(400, "Invalid company name.")

    if db.query(Company).filter(Company.slug == slug).first():
        slug = f"{slug}-{_mu_secrets.token_hex(3)}"

    company = create_company(
        db=db, name=name, slug=slug, is_active=True
    )

    db.execute(_mu_text("""
        INSERT INTO company_memberships (user_id, company_id)
        VALUES (:uid, :cid)
        ON CONFLICT (user_id, company_id) DO NOTHING
    """), {"uid": user["id"], "cid": company.id})
    db.execute(_mu_text("""
        UPDATE companies SET owner_user_id = :uid WHERE id = :cid
    """), {"uid": user["id"], "cid": company.id})
    db.commit()

    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug
    }



@router.delete("/current")
def delete_current_company(
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    company = get_workspace_company(authorization, x_company_id, db)
    actor_id = get_deletion_actor(authorization)

    db.execute(text("""
        ALTER TABLE companies
        ADD COLUMN IF NOT EXISTS owner_user_id BIGINT
    """))
    db.execute(text("""
        UPDATE companies c
        SET owner_user_id = (
            SELECT m.user_id FROM company_memberships m
            WHERE m.company_id = c.id
            ORDER BY m.created_at ASC, m.id ASC
            LIMIT 1
        )
        WHERE c.owner_user_id IS NULL
    """))
    owner_id = db.execute(text("""
        SELECT owner_user_id FROM companies WHERE id = :cid
    """), {"cid": company["id"]}).scalar()

    if owner_id is None or int(owner_id) != actor_id:
        raise HTTPException(403, "Only the company owner can delete this company.")

    company_record = db.query(Company).filter(Company.id == company["id"]).first()
    if not company_record:
        raise HTTPException(404, "Company not found.")

    record_deletion(
        db, "company", company_record.id, company_record.name,
        company_record.id, actor_id, "deactivated"
    )
    company_record.is_active = False
    db.commit()
    return {"success": True, "message": "Company deactivated and deletion recorded."}


@router.get("/support-email")
def get_support_email(
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    company = get_workspace_company(authorization, x_company_id, db)
    settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == company["id"]
    ).first()

    return {
        "support_email": settings.support_email if settings else None,
        "verified": bool(settings and settings.support_email_verified),
    }


@router.post("/support-email")
def set_support_email(
    data: dict,
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    company = get_workspace_company(authorization, x_company_id, db)
    email = str(data.get("email") or "").strip().lower()

    if len(email) > 320 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "Enter a valid support email address.")

    settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == company["id"]
    ).first()

    if not settings:
        settings = OrganizationSettings(organization_id=company["id"])
        db.add(settings)

    settings.support_email = email
    settings.support_email_verified = False

    db.query(SupportEmailVerification).filter(
        SupportEmailVerification.company_id == company["id"],
        SupportEmailVerification.verified_at.is_(None),
    ).delete(synchronize_session=False)

    raw_token = secrets.token_urlsafe(32)
    verification = SupportEmailVerification(
        company_id=company["id"],
        email=email,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(verification)
    db.commit()

    backend_url = (
        os.getenv("BACKEND_URL")
        or os.getenv("API_BASE_URL")
        or "http://127.0.0.1:8000"
    ).rstrip("/")
    verification_url = (
        f"{backend_url}/companies/verify-support-email?token={raw_token}"
    )

    sent, message = send_verification_email(email, verification_url)
    if not sent:
        raise HTTPException(503, message)

    return {
        "message": "Verification link sent to the support email.",
        "support_email": email,
        "verified": False,
    }


@router.get("/verify-support-email")
def verify_support_email(
    token: str,
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    verification = db.query(SupportEmailVerification).filter(
        SupportEmailVerification.token_hash == token_hash,
        SupportEmailVerification.verified_at.is_(None),
    ).first()

    if not verification:
        raise HTTPException(400, "Invalid or already-used verification link.")

    expires_at = verification.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Verification link has expired.")

    settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == verification.company_id
    ).first()

    if not settings:
        settings = OrganizationSettings(
            organization_id=verification.company_id
        )
        db.add(settings)

    settings.support_email = verification.email
    settings.support_email_verified = True
    verification.verified_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "message": "Support email verified successfully.",
        "support_email": verification.email,
        "verified": True,
    }

@router.get("/smtp-settings")
def get_company_smtp_settings(
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    company = get_workspace_company(authorization, x_company_id, db)

    settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == company["id"]
    ).first()

    smtp = (settings.settings or {}).get("smtp", {}) if settings else {}

    return {
        "host": smtp.get("host", ""),
        "port": smtp.get("port", 587),
        "username": smtp.get("username", ""),
        "security": smtp.get("security", "starttls"),
        "configured": bool(smtp.get("password_encrypted")),
    }


@router.post("/smtp-settings")
def save_company_smtp_settings(
    data: dict,
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    company = get_workspace_company(authorization, x_company_id, db)

    host = str(data.get("host") or "").strip()
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    security = str(data.get("security") or "starttls").lower()

    try:
        port = int(data.get("port", 587))
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid SMTP port.")

    if not host or not username or not password:
        raise HTTPException(400, "SMTP host, username and password are required.")

    if not 1 <= port <= 65535:
        raise HTTPException(400, "SMTP port must be between 1 and 65535.")

    if security not in ("ssl", "starttls"):
        raise HTTPException(400, "Security must be SSL or STARTTLS.")

    settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == company["id"]
    ).first()

    if not settings:
        settings = OrganizationSettings(organization_id=company["id"])
        db.add(settings)

    current_settings = dict(settings.settings or {})
    current_settings["smtp"] = {
        "host": host,
        "port": port,
        "username": username,
        "password_encrypted": encrypt_password(password),
        "security": security,
    }

    settings.settings = current_settings
    db.commit()

    return {
        "message": "Company SMTP settings saved securely.",
        "configured": True,
    }


@router.post("/smtp-settings/test")
def test_saved_company_smtp(
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    company = get_workspace_company(authorization, x_company_id, db)

    settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == company["id"]
    ).first()

    smtp = (settings.settings or {}).get("smtp", {}) if settings else {}

    if not smtp.get("password_encrypted"):
        raise HTTPException(400, "Save SMTP settings before testing.")

    success, message = test_company_smtp(smtp)

    if not success:
        raise HTTPException(400, message)

    return {"success": True, "message": message}

# ------------------------------------------------
# COMPANY SMTP SETTINGS
# ------------------------------------------------

@router.get("/smtp-settings")
def get_company_smtp_settings(
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    company = get_workspace_company(authorization, x_company_id, db)

    settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == company["id"]
    ).first()

    smtp = (settings.settings or {}).get("smtp", {}) if settings else {}

    return {
        "host": smtp.get("host", ""),
        "port": smtp.get("port", 587),
        "username": smtp.get("username", ""),
        "security": smtp.get("security", "starttls"),
        "configured": bool(smtp.get("password_encrypted")),
    }


@router.post("/smtp-settings")
def save_company_smtp_settings(
    data: dict,
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    from services.smtp_credentials import encrypt_password

    company = get_workspace_company(authorization, x_company_id, db)

    host = str(data.get("host") or "").strip()
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    security = str(data.get("security") or "starttls").strip().lower()

    try:
        port = int(data.get("port", 587))
    except (TypeError, ValueError):
        raise HTTPException(400, "SMTP port must be a number.")

    if not host:
        raise HTTPException(400, "SMTP host is required.")

    if not username:
        raise HTTPException(400, "SMTP username is required.")

    if not 1 <= port <= 65535:
        raise HTTPException(400, "SMTP port must be between 1 and 65535.")

    if security not in ["starttls", "ssl"]:
        raise HTTPException(400, "Security must be STARTTLS or SSL.")

    organization_settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == company["id"]
    ).first()

    if not organization_settings:
        organization_settings = OrganizationSettings(
            organization_id=company["id"],
            settings={}
        )
        db.add(organization_settings)

    company_settings = dict(organization_settings.settings or {})
    smtp_config = dict(company_settings.get("smtp", {}))

    # Keep the existing encrypted password if the password field is blank.
    if password:
        smtp_config["password_encrypted"] = encrypt_password(password)
    elif not smtp_config.get("password_encrypted"):
        raise HTTPException(400, "SMTP password is required.")

    smtp_config.update({
        "host": host,
        "port": port,
        "username": username,
        "security": security,
    })

    company_settings["smtp"] = smtp_config
    organization_settings.settings = company_settings

    db.commit()

    return {
        "message": "Company SMTP settings saved successfully.",
        "configured": True,
        "host": host,
        "port": port,
        "username": username,
        "security": security,
    }


@router.post("/smtp-settings/test")
def test_saved_company_smtp(
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    from services.smtp_credentials import test_company_smtp

    company = get_workspace_company(authorization, x_company_id, db)

    organization_settings = db.query(OrganizationSettings).filter(
        OrganizationSettings.organization_id == company["id"]
    ).first()

    smtp_config = (
        (organization_settings.settings or {}).get("smtp", {})
        if organization_settings else {}
    )

    if not smtp_config.get("password_encrypted"):
        raise HTTPException(400, "Save SMTP settings before testing.")

    success, message = test_company_smtp(smtp_config)

    return {
        "success": success,
        "message": message,
    }


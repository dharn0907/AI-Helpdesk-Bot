import re

from sqlalchemy.exc import IntegrityError

from database.models import Company, BotConfiguration


CONFIGURATION_FIELDS = {
    "bot_name",
    "what_this_bot_helps_with",
    "about_business",
    "how_to_respond",
    "when_to_handoff",
    "dos",
    "donts",
    "advanced_instructions",
}


def create_company(db, name, slug=None, is_active=True):
    """Register a company and create its default bot configuration."""

    name = str(name or "").strip()

    if not name:
        raise ValueError("Company name cannot be empty.")

    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", str(slug).lower()).strip("-")

    if not slug:
        raise ValueError("A valid company slug is required.")

    company = Company(
        name=name,
        slug=slug,
        is_active=is_active,
    )

    try:
        db.add(company)
        db.flush()

        configuration = BotConfiguration(
            company_id=company.id,
            bot_name="Support Assistant",
        )

        db.add(configuration)
        db.commit()
        db.refresh(company)

        return company

    except IntegrityError:
        db.rollback()
        raise ValueError(
            "A company with this slug or chatbot identity already exists."
        )

    except Exception:
        db.rollback()
        raise


def get_company_by_bot_public_id(db, bot_public_id):
    """Find an active company using its registered chatbot identity."""

    if not bot_public_id:
        return None

    return db.query(Company).filter(
        Company.bot_public_id == str(bot_public_id),
        Company.is_active.is_(True),
    ).first()


def get_bot_configuration(db, company_id):
    """Retrieve the configuration belonging to one company."""

    return db.query(BotConfiguration).filter(
        BotConfiguration.company_id == company_id
    ).first()


def update_bot_configuration(db, company_id, updates):
    """Update only the allowed configuration fields for a company."""

    if not isinstance(updates, dict):
        raise ValueError("Configuration updates must be an object.")

    unknown_fields = set(updates.keys()) - CONFIGURATION_FIELDS

    if unknown_fields:
        raise ValueError(
            "Unsupported configuration fields: "
            + ", ".join(sorted(unknown_fields))
        )

    company = db.query(Company).filter(
        Company.id == company_id,
        Company.is_active.is_(True),
    ).first()

    if not company:
        raise ValueError("Company not found or inactive.")

    configuration = get_bot_configuration(db, company_id)

    if not configuration:
        configuration = BotConfiguration(
            company_id=company_id,
            bot_name="Support Assistant",
        )
        db.add(configuration)

    for field, value in updates.items():
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field} must be a string.")

        setattr(configuration, field, value)

    try:
        db.commit()
        db.refresh(configuration)
        return configuration

    except Exception:
        db.rollback()
        raise

from pathlib import Path

p = Path("backend/services/workspace_auth.py")
s = p.read_text(encoding="utf-8")

if "def get_deletion_actor" not in s:
    s += '''

def get_deletion_actor(authorization):
    """Return the authenticated company user ID."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please log in.")
    try:
        secret = os.getenv("JWT_SECRET_KEY")
        payload = jwt.decode(
            authorization.split(" ", 1)[1],
            secret,
            algorithms=["HS256"]
        )
        if payload.get("type") != "user":
            raise ValueError("Invalid token")
        return int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Invalid or expired session.")


def record_deletion(db, entity_type, entity_id, entity_name, company_id, user_id):
    """Keep a permanent deletion record independent of the deleted entity."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS deletion_audit_logs (
            id BIGSERIAL PRIMARY KEY,
            entity_type VARCHAR(50) NOT NULL,
            entity_id VARCHAR(100) NOT NULL,
            entity_name TEXT,
            company_id INTEGER,
            deleted_by_user_id BIGINT NOT NULL,
            action VARCHAR(50) NOT NULL DEFAULT 'deactivated',
            deleted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.execute(text("""
        INSERT INTO deletion_audit_logs
        (entity_type, entity_id, entity_name, company_id, deleted_by_user_id, action)
        VALUES (:entity_type, :entity_id, :entity_name, :company_id, :user_id, 'deactivated')
    """), {
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "entity_name": entity_name,
        "company_id": company_id,
        "user_id": user_id,
    })
'''
    p.write_text(s, encoding="utf-8")

print("Deletion audit helper added.")

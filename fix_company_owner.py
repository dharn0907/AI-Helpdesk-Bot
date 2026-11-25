from pathlib import Path

p = Path("backend/routes/company_routes.py")
s = p.read_text(encoding="utf-8")

# Ensure ownership column exists and backfill existing companies.
create_anchor = '''    _mu_setup(db)
    user = _mu_get_user(authorization, db)
    name = str(data.get("name") or "").strip()
'''
create_replacement = '''    _mu_setup(db)
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
'''
if create_anchor not in s:
    raise SystemExit("Company creation anchor not found; stopped.")
s = s.replace(create_anchor, create_replacement, 1)

membership_anchor = '''    db.execute(_mu_text("""
        INSERT INTO company_memberships (user_id, company_id)
        VALUES (:uid, :cid)
        ON CONFLICT (user_id, company_id) DO NOTHING
    """), {"uid": user["id"], "cid": company.id})
    db.commit()
'''
membership_replacement = '''    db.execute(_mu_text("""
        INSERT INTO company_memberships (user_id, company_id)
        VALUES (:uid, :cid)
        ON CONFLICT (user_id, company_id) DO NOTHING
    """), {"uid": user["id"], "cid": company.id})
    db.execute(_mu_text("""
        UPDATE companies SET owner_user_id = :uid WHERE id = :cid
    """), {"uid": user["id"], "cid": company.id})
    db.commit()
'''
if membership_anchor not in s:
    raise SystemExit("Membership insertion anchor not found; stopped.")
s = s.replace(membership_anchor, membership_replacement, 1)

old_owner = '''    # The first user linked to the company is treated as its creator/owner.
    owner_id = db.execute(text("""
        SELECT user_id FROM company_memberships
        WHERE company_id = :cid
        ORDER BY created_at ASC, id ASC
        LIMIT 1
    """), {"cid": company["id"]}).scalar()
'''
new_owner = '''    db.execute(text("""
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
'''
if old_owner not in s:
    raise SystemExit("Old owner check not found; stopped.")
s = s.replace(old_owner, new_owner, 1)

p.write_text(s, encoding="utf-8")
print("Explicit company ownership added.")

from pathlib import Path

# Update audit helper to support revoked/deactivated actions
p = Path("backend/services/workspace_auth.py")
s = p.read_text(encoding="utf-8")
s = s.replace(
    "def record_deletion(db, entity_type, entity_id, entity_name, company_id, user_id):",
    "def record_deletion(db, entity_type, entity_id, entity_name, company_id, user_id, action='deactivated'):"
)
s = s.replace(
    "VALUES (:entity_type, :entity_id, :entity_name, :company_id, :user_id, 'deactivated')",
    "VALUES (:entity_type, :entity_id, :entity_name, :company_id, :user_id, :action)"
)
s = s.replace(
    '"user_id": user_id,\n    })',
    '"user_id": user_id,\n        "action": action,\n    })'
)
p.write_text(s, encoding="utf-8")

# Company owner-only deactivation endpoint
p = Path("backend/routes/company_routes.py")
s = p.read_text(encoding="utf-8")
if "def delete_current_company" not in s:
    s = s.replace(
        "from services.workspace_auth import get_workspace_company",
        "from services.workspace_auth import get_workspace_company, get_deletion_actor, record_deletion"
    )
    s += '''

@router.delete("/current")
def delete_current_company(
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    company = get_workspace_company(authorization, x_company_id, db)
    actor_id = get_deletion_actor(authorization)

    # The first user linked to the company is treated as its creator/owner.
    owner_id = db.execute(text("""
        SELECT user_id FROM company_memberships
        WHERE company_id = :cid
        ORDER BY created_at ASC, id ASC
        LIMIT 1
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
'''
    p.write_text(s, encoding="utf-8")

# Agent revoke endpoint
p = Path("backend/routes/ticket_routes.py")
s = p.read_text(encoding="utf-8")
if "def revoke_support_agent" not in s:
    s = s.replace(
        "from services.workspace_auth import get_workspace_company",
        "from services.workspace_auth import get_workspace_company, get_deletion_actor, record_deletion"
    )
    s += '''

@router.delete("/agents/{agent_id}")
def revoke_support_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    authorization: str = Header(default=None),
    x_company_id: int = Header(default=None, alias="X-Company-ID"),
):
    company = get_workspace_company(authorization, x_company_id, db)
    actor_id = get_deletion_actor(authorization)

    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == agent_id,
        OrganizationMember.organization_id == company["id"],
        OrganizationMember.role == "support_agent",
    ).first()

    if not member:
        raise HTTPException(404, "Support agent not found.")

    record_deletion(
        db, "support_agent", member.id, member.email,
        company["id"], actor_id, "revoked"
    )
    member.status = "revoked"
    db.commit()
    return {"success": True, "message": "Support agent access revoked."}
'''
    p.write_text(s, encoding="utf-8")

print("Company deactivation and agent revocation endpoints added.")

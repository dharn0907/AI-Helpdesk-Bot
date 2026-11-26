# Orbit — Internal Platform Monitoring Dashboard

A separate React/Vite application for the third website described in the Internal Platform Monitoring & Super Admin Dashboard specification.

## Important integration status

This repository currently has a React/Vite company-facing frontend and a FastAPI backend. The dashboard is isolated in `internal-dashboard/` and does not alter either existing application.

The UI runs in **demo mode** when `VITE_API_BASE_URL` is not set. All displayed records and metrics are illustrative sample data. They are never represented as live production data.

The current backend repository does **not** expose a verified internal super-admin API or a separate internal-admin authentication flow. Do not point this frontend at production data until those backend controls exist. The company login token is not a substitute for an internal admin identity.

## Run locally

```bash
cd internal-dashboard
npm install
npm run dev
```

Open `http://localhost:5175`.

Build:

```bash
npm run build
```

## Backend integration contract

After the backend team implements the routes below with independent internal-admin authentication and server-side RBAC, configure:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Expected endpoints (proposed contract, not currently verified as implemented):

- `POST /api/internal/auth/login`
- `POST /api/internal/auth/logout`
- `GET /api/internal/me`
- `GET /api/internal/health`
- `GET /api/internal/overview?range=7d`
- `GET /api/internal/companies?page=1&page_size=25&search=`
- `GET /api/internal/chatbots?page=1&page_size=25`
- `GET /api/internal/conversations?page=1&page_size=25`
- `GET /api/internal/conversations/{id}`
- `GET /api/internal/tickets?page=1&page_size=25`
- `GET /api/internal/customers?page=1&page_size=25`
- `GET /api/internal/agents?page=1&page_size=25`
- `GET /api/internal/analytics?range=7d`
- `GET /api/internal/ai-events?page=1&page_size=25`
- `GET /api/internal/system-logs?page=1&page_size=25`
- `GET /api/internal/admin-users`

### Required backend security

1. Create a separate internal-admin identity store/allowlist. Never authenticate this site with a company account.
2. Enforce roles on every `/api/internal/*` route. Frontend route hiding is not authorization.
3. Use the existing database and SQLAlchemy models; do not duplicate platform entities.
4. Scope customer identities by `(company_id, customer_identifier)`; do not merge the same email/ID across tenants without a verified global identity model.
5. Return only fields required for monitoring. Redact secrets, tokens, credentials, and sensitive message content.
6. Add audit records for privileged actions. Keep this dashboard read-only initially.
7. Health indicators must come from real health probes, not constants.
8. Add pagination, server-side filtering, validation, rate limiting, and appropriate CORS.

## Repository observations

- Existing company-facing frontend: `frontend/` (React 19 + Vite).
- Existing backend: `backend/` (FastAPI + SQLAlchemy).
- Existing model definitions include companies, bot configuration, tickets, conversations/messages, knowledge-base records, and historical solution/review records.
- The repository README describes a FastAPI + React helpdesk chatbot platform.
- No live database credentials or DB connection are required to build this isolated UI.

## Next integration phase

The internal API must be implemented in the FastAPI backend on the machine/environment that has the database connection. The dashboard can be developed and built independently here; actual live metrics cannot be verified until the backend and database are reachable.

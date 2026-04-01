# Finance Data Processing & Access Control Backend

A production-grade FastAPI backend for managing financial records with role-based access control, immutable audit trails, and idempotent transaction creation.

## Quick Start

```bash
# one command — spins up Postgres + seeds 3 users + 150 records + starts API
make up

# then open Swagger UI
open http://localhost:8000/docs
```

### Seeded Credentials

| Role | Email | Password |
|---|---|---|
| **Admin** | admin@zorvyn.io | admin1234 |
| **Analyst** | analyst@zorvyn.io | analyst1234 |
| **Viewer** | viewer@zorvyn.io | viewer1234 |

## Architecture

```
app/
├── main.py              ← FastAPI app, lifespan, CORS, exception handlers
├── config.py            ← Pydantic Settings (env vars)
├── database.py          ← Async SQLAlchemy engine + session dependency
├── models.py            ← 4 ORM models with indexes and constraints
├── schemas.py           ← Pydantic request/response schemas
├── security.py          ← JWT + bcrypt utilities
├── rbac.py              ← Role enforcement via dependency injection
├── routes/              ← API endpoints (auth, users, records, dashboard, health)
└── services/            ← Business logic (user_ops, record_ops, dashboard_ops)
```

## Tech Stack

- **Framework**: FastAPI (async)
- **Database**: PostgreSQL 16 via SQLAlchemy 2.0 (asyncpg driver)
- **Auth**: JWT (HS256) with bcrypt password hashing
- **Containerization**: Docker + Docker Compose
- **Testing**: pytest + httpx AsyncClient

## API Endpoints

### Auth (Public)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create a new user (default: viewer role) |
| POST | `/auth/login` | Get JWT access token |

### Users (Admin only)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/users` | List all users (filterable by role, status) |
| GET | `/users/{id}` | Get single user |
| PATCH | `/users/{id}` | Update role or active status |

### Financial Records (Role-gated)
| Method | Endpoint | Minimum Role | Description |
|---|---|---|---|
| POST | `/records` | Admin | Create record (supports `Idempotency-Key` header) |
| GET | `/records` | Analyst | List with filters + pagination |
| GET | `/records/{id}` | Analyst | Get single record |
| PATCH | `/records/{id}` | Admin | Update (optimistic concurrency via `expected_updated_at`) |
| DELETE | `/records/{id}` | Admin | Soft delete |

### Dashboard (Viewer+)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard/summary` | Total income, expenses, net balance, record count |
| GET | `/dashboard/category-breakdown` | Totals grouped by category and type |
| GET | `/dashboard/trends` | Monthly income vs expenses |
| GET | `/dashboard/recent-activity` | Last N records created |

### Health (Public)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | DB connectivity check |

## Key Design Decisions

### 1. Currency as NUMERIC(15,2) — Not Float
Floating-point arithmetic introduces rounding errors in financial calculations. All amounts are stored as `NUMERIC(15,2)` in Postgres and `Decimal` in Python. Pydantic serializes them as strings in JSON to prevent IEEE 754 precision loss on the wire.

### 2. Idempotency Keys for Record Creation
Duplicate POST prevention via an `Idempotency-Key` header. If the same key is sent within 24 hours, the original `201 Created` response is returned without creating a duplicate record. Keys are stored in the `idempotency_keys` table and purged on app startup.

### 3. Immutable Audit Trail
Every `CREATE`, `UPDATE`, and `DELETE` on financial records writes a row to `record_audit_logs` containing the old payload, new payload, who made the change, and when. This is separate from `updated_at` — it creates a full, queryable history of what changed and who did it.

### 4. Optimistic Concurrency Control
Updates require an `expected_updated_at` timestamp. If the record was modified by another request between read and write, the server returns `409 Conflict` instead of silently overwriting.

### 5. Soft Deletes
Financial records are never physically deleted. A `deleted_at` timestamp is set, and all queries filter `WHERE deleted_at IS NULL`. A partial index on this column ensures active-record queries don't scan tombstones.

### 6. RBAC via Dependency Injection
Roles (admin > analyst > viewer) are enforced at the API boundary using FastAPI's `Depends()` system. The `require_role()` factory returns a dependency that checks the caller's JWT-derived role against a hierarchy. No middleware bypass is possible.

## Database Schema

### Tables
- **users** — id, email, username, hashed_password, role, is_active, timestamps
- **financial_records** — id, amount (NUMERIC), type, category, description, date, created_by (FK), timestamps, deleted_at
- **record_audit_logs** — id, record_id (FK), action, changed_by (FK), old_payload (JSONB), new_payload (JSONB), changed_at
- **idempotency_keys** — key (PK), user_id (FK), response_code, response_body (JSONB), created_at

### Performance Indexes
- `ix_records_type_date` — composite on `(record_type, record_date)` for dashboard aggregations
- `ix_records_category` — category-wise breakdown queries
- `ix_records_active` — partial index `WHERE deleted_at IS NULL` to skip tombstones
- `ix_audit_record_id` — audit history lookups per record

## Makefile Commands

```bash
make up        # Build and start everything (Postgres + app + seed)
make down      # Stop containers
make restart   # Rebuild and restart
make logs      # Tail app logs
make seed      # Re-run seed script manually
make test      # Run pytest inside container
make clean     # Stop containers AND delete volumes (fresh start)
```

## Running Tests

```bash
make test
# or directly:
docker compose exec app pytest tests/ -v --tb=short
```

## Assumptions & Tradeoffs

1. **No refresh tokens**: Single JWT access token for simplicity. In production, pair with refresh tokens or use short-lived tokens + session store.
2. **Table auto-creation on startup**: `Base.metadata.create_all` in lifespan for dev convenience. Alembic migrations are set up for production use.
3. **Seed script is idempotent**: Checks for existing `admin@zorvyn.io` before inserting. Safe to re-run.
4. **CORS allows all origins**: Appropriate for local dev. Lock down in production.
5. **Viewer can only access dashboard**: Viewers cannot list individual financial records — only aggregated dashboard data. Analysts can read records. Admins have full access.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/finance_db` | Async Postgres connection string |
| `JWT_SECRET` | `change-me-to-a-long-random-string` | HMAC signing key for JWTs |
| `JWT_EXPIRY_MINUTES` | `60` | Token validity period |

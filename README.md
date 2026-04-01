# Zorvyn — Finance Data Processing & Access Control

A production-grade backend service for managing financial records, role-based access control (RBAC), and dashboard aggregations. Built with FastAPI and async PostgreSQL.

## Quick Start (Reviewer Experience)

I respect your time. This project includes a seed script that automatically populates the database with users and 150 randomized financial records spanning the last 6 months so you can instantly test the dashboard aggregations.

**1. Start the system (requires Docker):**
```bash
make up
```
This spins up the Postgres 16 database, creates all tables, starts the FastAPI application, and injects the seed data.

**2. Access the API & Documentation:**
- **Swagger UI / OpenAPI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

**3. Seeded Test Credentials:**

| Role | Email | Password | Access Level |
|---|---|---|---|
| **Admin** | `admin@zorvyn.dev` | `password123` | Full access |
| **Analyst** | `analyst@zorvyn.dev` | `password123` | Read-only records + Dashboard |
| **Viewer** | `viewer@zorvyn.dev` | `password123` | Dashboard only |

**4. Run the Test Suite:**
```bash
make test
```

---

## Architectural Decisions & Trade-offs

| Decision | Implementation | Rationale |
|----------|---------------|-----------|
| **Framework** | FastAPI (Python 3.12) | Native async support, automatic OpenAPI docs, Pydantic validation catches invalid input before database touch |
| **Database** | PostgreSQL 16 + SQLAlchemy 2.0 async | Currency stored as `NUMERIC(15,2)` instead of float to eliminate IEEE 754 precision errors. All amounts serialized as strings in JSON responses. |
| **Authentication** | JWT (HS256) + bcrypt | Single access token model (deliberate simplification). In production, would pair with short-lived tokens + refresh flow. |
| **Access Control** | RBAC via FastAPI dependency injection | `Depends(require_role("admin"))` rejects unauthorized requests before route handler executes — no middleware bypass possible |
| **Concurrency** | Optimistic locking via `expected_updated_at` | Two admins updating same record simultaneously → second request fails with 409 Conflict instead of silent overwrite |
| **Idempotency** | `POST /records` accepts `Idempotency-Key` header | Duplicate submissions within 24 hours return cached response without creating duplicate transactions — critical for financial systems with network retries |
| **Audit Trail** | Immutable `record_audit_logs` table | Every UPDATE/DELETE inserts row with full JSON snapshots of old/new payloads, user ID, timestamp. Append-only, immutable. |
| **Soft Deletes** | `deleted_at` timestamp with partial index | Records never hard-deleted. Partial index `WHERE deleted_at IS NULL` ensures active queries skip tombstones without scanning them. |
| **Rate Limiting** | slowapi | 60 req/min global, 10/min on login (brute-force), 5/min on registration (spam prevention) |
| **Testing** | 80 integration tests | pytest + httpx AsyncClient covering CRUD, RBAC, edge cases (zero/negative amounts, stale concurrency, double-delete), decimal precision |

---

## Architecture & Engineering Decisions

This backend was designed with the strict data integrity and security requirements of a financial system in mind.

### 1. Ironclad RBAC at the Dependency Layer

Instead of relying on fragile UI checks or complex middleware, role enforcement is strictly handled via FastAPI Dependency Injection (`Depends(require_role("admin"))`). If a Viewer attempts to hit `DELETE /records/{id}`, the request is rejected with a `403 Forbidden` before it ever reaches the route handler or database session.

### 2. Financial Data Integrity

- **No Floating-Point Math**: Currency is stored using PostgreSQL's native `NUMERIC(15,2)` to prevent IEEE 754 precision loss. Pydantic handles the serialization to strings for the JSON responses.
- **Idempotency on Creation**: The `POST /records` endpoint requires an `Idempotency-Key` header. This prevents duplicate transactions if a client retries a request due to network instability.

### 3. Concurrency & Auditability

- **Optimistic Locking**: Concurrent updates to the same financial record are prevented using an `updated_at` version check. If two admins update the same record simultaneously, the second request safely fails with a `409 Conflict`.
- **Immutable Audit Trail**: Financial systems require strict compliance. Every `UPDATE` or `DELETE` triggers a database-level insertion into a `record_audit_logs` table, storing the exact `old_payload` and `new_payload` alongside the user ID.
- **Soft Deletes**: Records are never hard-deleted. They receive a `deleted_at` timestamp. Partial database indexes (`WHERE deleted_at IS NULL`) ensure that live queries and dashboard aggregations remain blazingly fast without scanning tombstone data.

### 4. High-Performance Aggregations

Dashboard metrics (e.g., total income, category breakdowns) are calculated using native SQLAlchemy aggregate functions (`func.sum`, `extract('month')`) directly in the PostgreSQL database, rather than fetching thousands of rows into Python memory.

### 5. Rate Limiting

All endpoints are globally rate-limited to **60 requests/minute per IP** via `slowapi`. Sensitive endpoints have stricter per-route limits:
- `POST /auth/login` — **10/minute** (brute-force protection)
- `POST /auth/register` — **5/minute** (spam prevention)

Exceeding the limit returns `429 Too Many Requests` with a `Retry-After` header.

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI (Python 3.12) |
| **Database** | PostgreSQL 16 |
| **ORM** | SQLAlchemy 2.0 (Asyncpg driver) |
| **Migrations** | Alembic |
| **Authentication** | JWT (PyJWT) + bcrypt |
| **Rate Limiting** | slowapi (in-memory, per-IP) |
| **Testing** | Pytest + HTTPX |
| **Containerization** | Docker + Docker Compose |

---

## Project Structure

```
zorvyn/
├── app/
│   ├── routes/          # FastAPI endpoints (auth, users, records, dashboard, health)
│   ├── services/        # Core business logic, idempotency, and DB queries
│   ├── models.py        # SQLAlchemy ORM models (4 tables)
│   ├── schemas.py       # Pydantic validation schemas
│   ├── security.py      # JWT encoding and password hashing
│   ├── rbac.py          # Role-based access control dependencies
│   ├── rate_limit.py    # slowapi limiter instance
│   ├── config.py        # Pydantic Settings (env vars)
│   ├── database.py      # Async engine + session factory
│   └── main.py          # App entrypoint, lifespan, CORS
├── scripts/
│   └── seed_db.py       # Database seeding automation
├── tests/               # Pytest suite with fixtures per role
├── alembic/             # Database migration configuration
├── Makefile             # Developer workflow commands
├── Dockerfile           # Python 3.12 container
└── docker-compose.yml   # Postgres + app orchestration
```

---

## API Reference

### Auth (Public)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a new user (default: viewer) |
| `POST` | `/auth/login` | Get JWT access token |

### Users (Admin only)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/users` | List all users (filterable by role, status) |
| `GET` | `/users/{id}` | Get single user |
| `PATCH` | `/users/{id}` | Update role or active status |

### Financial Records (Role-gated)
| Method | Endpoint | Min. Role | Description |
|---|---|---|---|
| `POST` | `/records` | Admin | Create record (requires `Idempotency-Key` header) |
| `GET` | `/records` | Analyst | List with filters + pagination |
| `GET` | `/records/{id}` | Analyst | Get single record |
| `PATCH` | `/records/{id}` | Admin | Update (optimistic concurrency via `expected_updated_at`) |
| `DELETE` | `/records/{id}` | Admin | Soft delete |

### Dashboard (Viewer+)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/dashboard/summary` | Total income, expenses, net balance, record count |
| `GET` | `/dashboard/category-breakdown` | Totals grouped by category and type |
| `GET` | `/dashboard/trends` | Monthly income vs expenses |
| `GET` | `/dashboard/recent-activity` | Last N records created |

### Health (Public)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Database connectivity check |

---

## Database Schema

### Tables
- **`users`** — id (UUID), email, username, hashed_password, role (enum), is_active, timestamps
- **`financial_records`** — id (UUID), amount (`NUMERIC(15,2)`), type (enum), category, description, date, created_by (FK), timestamps, `deleted_at`
- **`record_audit_logs`** — id (UUID), record_id (FK), action (enum), changed_by (FK), `old_payload` (JSONB), `new_payload` (JSONB), changed_at
- **`idempotency_keys`** — key (PK), user_id (FK), response_code, response_body (JSONB), created_at (24h TTL)

### Performance Indexes
- `ix_records_type_date` — composite on `(record_type, record_date)` for dashboard aggregations
- `ix_records_category` — category-wise breakdown queries
- `ix_records_active` — partial index `WHERE deleted_at IS NULL` to skip tombstones
- `ix_audit_record_id` — audit history lookups per record

---

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

---

## Assumptions & Tradeoffs

1. **Single JWT access token** — No refresh token complexity. In production, pair with refresh tokens or use short-lived tokens + session store.
2. **Table auto-creation on startup** — `Base.metadata.create_all` in the lifespan for dev convenience. Alembic migrations are configured for production use.
3. **Idempotent seed script** — Checks for existing admin user before inserting. Safe to re-run.
4. **CORS allows all origins** — Appropriate for local development. Must be locked down in production.
5. **Viewer access is dashboard-only** — Viewers cannot list individual financial records. Only aggregated dashboard data is accessible.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/finance_db` | Async Postgres connection string |
| `JWT_SECRET` | `change-me-to-a-long-random-string` | HMAC signing key for JWTs |
| `JWT_EXPIRY_MINUTES` | `60` | Token validity period |

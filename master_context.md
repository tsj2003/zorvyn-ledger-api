# Master Context History

This document serves as a portable knowledge base compiling all recent conversations, established formatting rules, career objectives, and ongoing projects. Providing this file to a new chat session will instantly restore the complete context required to continue tasks seamlessly without losing critical templates or project data.

---

## 1. Professional Outreach & Application Strategy
*Last Active: Conversations bfe671b8... & 56fec9dd... & 17559208...*

**Objective:** Secure high-quality SDE and AI-related internships or entry-level full-time roles (AI Engineer, Software Development Engineer) at top-tier companies (Barclays, UBS, IDFC First, Meta, Aikenist, Browser Use).

**Key Differentiators & Assets:**
- Strong technical proficiency in **Python, PyTorch**, and production deployment tools like **Docker and Kubernetes**.
- Specialized experience in medical imaging applications (critical for the Aikenist AI Engineer application).
- Verified production experience and significant competitive programming achievements.
- Real-world AI project portfolio demonstrating end-to-end capability.

**Outreach Approach (Advanced Prompting Framework):**
- **Format:** High-conversion, human-sounding, concise, and fact-based LinkedIn outreach and cold emails.
- **Goal:** Maximize conversion rates for referrals and initial recruiter screenings, tailored individually per company founder/recruiter (e.g., specific tailored outreach to Magnus for Browser Use internship).

---

## 2. Technical Projects & Active Deployments

### Project Alpha: SAP Order-to-Cash Context Graph System
*Last Active: Conversation bf7cf377...*
- **Current Status:** Finalizing and packaging for deployment.
- **Core Requirements:** Clean codebase, properly tracking dependencies, configuring cloud environment variables for both backend and frontend.
- **End Goal:** Push the entire production-ready repository to GitHub for assignment submission. A live demo link and public source code are mandatory deliverables.

### Project Beta: Finance Data Processing and Access Control Backend (Zorvyn)
*Last Active: Current Session*
- **Current Status:** Full implementation complete on the local machine (`/Users/tarandeepsinghjuneja/zorvyn`).
- **Tech Stack:** FastAPI, PostgreSQL (asyncpg), SQLAlchemy, Alembic, Docker.
- **Core Features Implemented:**
  - Strict RBAC strategy evaluated at the dependency layer (`Admin`, `Analyst`, `Viewer`).
  - Immutable audit trails tracking every change within `record_audit_logs`.
  - Idempotency Keys preventing duplicate POSTs on network retries.
  - Financial records precision maintained through strings and `NUMERIC(15,2)` DB types to avoid float inaccuracies.
  - Automated deployment logic (Dockerfile, `docker-compose.yml`, Makefile) and `scripts/seed_db.py` for reviewer experience.

---

## 3. Communication Style & Persona Constraints
*Last Active: Conversation 54ebafac...*

When assisting with code or outreach, the AI must strictly adhere to the established "Pragmatic Senior Developer" and "Advanced Prompting Framework" constraints:
- **Zero Boilerplate:** Only document complex logic; never write generic comments.
- **Opinionated Naming:** Use domain-contextual variable naming. Never use `data`, `result`, `item`, or `response`.
- **Direct Implementation:** Favor functional, slightly raw code over unnecessary abstractions. No over-engineering.
- **No Fluff:** Output pure code or required data without introductory or concluding remarks.

*(Save this document and upload it via context or file attachment in any new session to successfully hard-load all ongoing constraints and statuses.)*

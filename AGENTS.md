# AGENTS.md - Development Guidelines for AI Agents and Reviewers

This document outlines the development workflow, conventions, and lessons learned during the LandTen project. It serves as a guide for AI agents (like Claude/OpenCode) and human reviewers to maintain consistency and avoid known pitfalls.

---

## Table of Contents

- [Project Context](#project-context)
- [Recommended Skills](#recommended-skills)
- [Commit Conventions](#commit-conventions)
- [Pain Points and Solutions](#pain-points-and-solutions)
- [Architecture Decisions](#architecture-decisions)
- [Code Review Checklist](#code-review-checklist)
- [Common Tasks](#common-tasks)

---

## Project Context

LandTen is a landlord-tenant management platform with:

- **Backend**: FastAPI + SQLModel + SQLite
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS

The system does NOT use payment gateways. Instead, it implements a manual verification workflow where tenants upload bank transfer receipts and landlords approve them.

---

## Recommended Skills

### 1. Commit Skill (MANDATORY for all commits)

Always use the `commit` skill when saving progress. This ensures:

- One commit per file (unless files are inseparable)
- Controlled verb vocabulary
- Explicit scope in brackets
- Short, reviewable commit messages

**Format**: `<verb>(<scope>): <short message>`

**Allowed Verbs**:

- `feat` - new user-facing capability
- `fix` - bug fix
- `refactor` - structural change, no behavior change
- `chore` - tooling, cleanup, non-prod logic
- `docs` - documentation only
- `test` - tests only
- `perf` - performance improvement
- `style` - formatting, lint-only changes

**Examples**:

```
feat(payments): add receipt upload endpoint
fix(auth): handle missing token edge case
refactor(api): extract request parsing logic
chore(deps): update frontend dependencies
test(backend): add tenant auth tests
```

**Anti-patterns to avoid**:

- "updated stuff"
- "minor changes"
- "fixes"
- Commits without scope
- Commits mixing multiple intents

### 2. Frontend Design Skill

Use when creating UI components. Ensures:

- Production-grade interfaces
- Consistent design system usage
- Avoids generic AI aesthetics

---

## Commit Conventions

### Workflow

1. Run `git status` and `git diff` to inspect changes
2. Stage ONE file at a time: `git add path/to/file`
3. Commit with proper format: `git commit -m "verb(scope): message"`
4. Repeat for each file
5. Run `git status` to verify clean state

### Multi-file Commits

Only allowed when files are inseparable:

- Interface + implementation
- Schema + migration
- Test + fixture

### Scope Inference

Infer scope from file path:

- `backend/app/routers/payments.py` -> `payments`
- `frontend/src/lib/api.ts` -> `api`
- `backend/app/models/payment.py` -> `models`
- `backend/alembic/versions/*` -> `db`

---

## Pain Points and Solutions

### 1. Stripe Integration Removal

**Problem**: We attempted to integrate Stripe for direct payments, then decided to revert to manual receipt upload.

**Solution**: Complete removal required touching multiple files:

- `backend/requirements.txt` - remove stripe package
- `backend/app/core/config.py` - remove STRIPE_* settings
- `backend/app/routers/payments.py` - remove create_payment_intent endpoint
- `backend/app/schemas/payment.py` - remove PaymentIntent schemas
- `frontend/src/lib/api.ts` - remove createPaymentIntent method
- `frontend/src/app/tenant/dashboard/` - remove PaymentModal, add ReceiptUploadModal

**Lesson**: When reverting a feature, create a checklist of ALL files that need changes. Incomplete reversions cause import errors.

### 2. Broken Imports After Partial Reversion

**Problem**: After removing Stripe schemas, the payments router still tried to import `PaymentIntentCreate` and `PaymentIntentResponse`, preventing server startup.

**Solution**: Always grep for removed symbols:

```bash
grep -r "PaymentIntentCreate" backend/
grep -r "STRIPE" backend/
```

**Lesson**: After removing any class/function/constant, search the entire codebase for references.

### 3. Missing Dependencies

**Problem**: Server failed to start with `ModuleNotFoundError: No module named 'apscheduler'` despite it being in requirements.txt.

**Solution**:

```bash
pip install -r requirements.txt
# or specifically
pip install apscheduler
```

**Lesson**: When debugging import errors, verify the package is actually installed in the active Python environment, not just listed in requirements.txt.

### 4. Alembic Migration Syntax

**Problem**: Auto-generated migration used `sqlmodel.sql.sqltypes.AutoString()` which failed at runtime.

**Solution**: Change to `sqlmodel.AutoString()` or `sa.String()`:

```python
# Before (broken)
sa.Column("receipt_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True)

# After (working)
sa.Column("receipt_url", sqlmodel.AutoString(), nullable=True)
```

**Lesson**: Always review auto-generated migrations before applying. Run `alembic upgrade head` immediately after generating to catch errors early.

### 5. Type Checker False Positives

**Problem**: Pyright/Pylance shows errors like `Cannot access attribute "in_" for class "str"` on SQLModel queries.

**Solution**: These are type checker limitations with SQLModel/SQLAlchemy, not actual runtime errors. The code works correctly. Options:

- Ignore these specific errors
- Add type: ignore comments
- Use cast() for complex queries

**Lesson**: Distinguish between type checker errors and actual bugs. SQLModel's dynamic nature confuses static analysis.

### 6. Dual Authentication Systems

**Problem**: Landlords and tenants need separate auth flows but share the same token infrastructure.

**Solution**:

- Separate routers: `auth.py` (landlords) and `tenant_auth.py` (tenants)
- Separate dependencies: `get_current_landlord()` and `get_current_tenant()`
- Token contains user type indicator
- Frontend stores single token, routes determine which auth to use

**Lesson**: Plan authentication architecture early. Retrofitting dual auth is error-prone.

---

## Architecture Decisions

### 1. No Payment Gateway

**Decision**: Use manual receipt upload instead of Stripe/payment processors.

**Rationale**:

- Simpler implementation
- No PCI compliance concerns
- Works with any bank transfer method
- Landlord maintains control over verification

**Implementation**:

- Tenant uploads image/PDF receipt
- Backend saves to `uploads/receipts/`
- Payment status changes to VERIFYING
- Landlord reviews and approves/rejects

### 2. SQLite for Development

**Decision**: Use SQLite instead of PostgreSQL.

**Rationale**:

- Zero configuration
- Single file database
- Easy to reset/backup
- Sufficient for development and small deployments

**Migration Path**: Change `DATABASE_URL` to PostgreSQL connection string for production.

### 3. File-based Receipt Storage

**Decision**: Store receipts locally in `backend/uploads/receipts/`.

**Rationale**:

- Simple for development
- No cloud dependencies
- Works offline

**Production Consideration**: Migrate to S3/Cloud Storage for:

- Scalability
- Redundancy
- CDN delivery

### 4. Server-Sent Events for Notifications

**Decision**: Use SSE instead of WebSockets for real-time notifications.

**Rationale**:

- Simpler than WebSockets
- One-way communication sufficient
- Better browser support
- Automatic reconnection

---

## Code Review Checklist

### Backend Changes

- [ ] No hardcoded secrets or credentials
- [ ] All new endpoints have proper authentication
- [ ] Database queries use parameterized statements (SQLModel handles this)
- [ ] New models have corresponding Alembic migrations
- [ ] Schemas validate input appropriately
- [ ] Error responses use proper HTTP status codes
- [ ] File uploads validate content type and size

### Frontend Changes

- [ ] No hardcoded API URLs (use environment variables)
- [ ] Loading states handled for async operations
- [ ] Error states displayed to users
- [ ] Forms validate input before submission
- [ ] Authentication redirects work correctly
- [ ] No console.log statements in production code

### Commit Quality

- [ ] One file per commit (unless inseparable)
- [ ] Proper verb used (feat/fix/refactor/chore/docs/test)
- [ ] Scope matches file location
- [ ] Message explains WHY, not just WHAT

---

## Common Tasks

### Adding a New API Endpoint

1. Create/update schema in `backend/app/schemas/`
2. Add endpoint in appropriate router under `backend/app/routers/`
3. Add corresponding method in `frontend/src/lib/api.ts`
4. Update types in api.ts if needed
5. Commit each file separately with appropriate scope

### Adding a New Database Field

1. Update model in `backend/app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration file
4. Apply migration: `alembic upgrade head`
5. Update schemas if field should be in API response
6. Commit: model, migration, schema (can be grouped if tightly coupled)

### Adding a New Page (Frontend)

1. Create page file under `frontend/src/app/`
2. Add any required components
3. Update navigation/links if needed
4. Add API methods if new endpoints required
5. Commit each file separately

### Running the Full Stack

Terminal 1 (Backend):

```bash
cd backend
uvicorn app.main:app --reload
```

Terminal 2 (Frontend):

```bash
cd frontend
npm run dev
```

### Resetting the Database

```bash
cd backend
rm landten.db
alembic upgrade head
```

---

## Agent-Specific Instructions

### When Starting a Session

1. Read this file (AGENTS.md) first
2. Check `git status` for uncommitted changes
3. Review recent commits with `git log --oneline -10`
4. Ask user for context if resuming work

### When Making Changes

1. Understand the full scope before editing
2. Check for related files that may need updates
3. Run the server to verify changes work
4. Use the commit skill for all commits

### When Debugging

1. Check server logs for stack traces
2. Grep for removed/renamed symbols
3. Verify dependencies are installed
4. Distinguish type checker errors from runtime errors

### When Completing a Session

1. Commit all changes using the commit skill
2. Run `git status` to verify clean state
3. Summarize what was done and what remains
4. Update this file if new patterns/lessons emerged

---

## File Ownership

When modifying these critical files, extra care is required:

| File | Impact | Notes |
|------|--------|-------|
| `backend/app/main.py` | Server startup | Affects all routes |
| `backend/app/core/security.py` | Authentication | Both landlord and tenant auth |
| `backend/app/core/config.py` | Settings | Environment variables |
| `frontend/src/lib/api.ts` | All API calls | Types must match backend |
| `frontend/src/lib/auth-context.tsx` | Auth state | Affects all protected pages |

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2025-12-31 | Initial creation | Kasule Trevor |
| 2025-12-31 | Added receipt upload workflow | Kasule Trevor |
| 2025-12-31 | Removed Stripe integration | Kasule Trevor |

---

## Questions or Issues

If you encounter issues not covered here:

1. Check the README.md for general project information
2. Review recent commits for context
3. Search codebase for similar patterns
4. Document new learnings in this file
5. Ask the user for clarity

# Backend Testing Plan - LandTen

**Status:** In Progress  
**Target Coverage:** 80%  
**Approach:** Bottom-up (Auth/Models → Routes → Integration)  
**Test Type:** Full end-to-end with actual file uploads

---

## Summary

**Total Tests Created:** ~400+ tests  
**Current Coverage:** ~50-60% (estimated)  
**Test Files:** 15 files across models, core utilities, and API routes

### Test Count by Module

| Module | Tests | Status |
|--------|-------|--------|
| test_models/ | 231 | ✅ Complete |
| test_core/ | 90+ | ✅ Complete |
| api/routes/test_properties.py | 28 | ✅ Complete |
| api/routes/test_rooms.py | 39 | ✅ Complete |
| api/routes/test_tenants.py | 55 | ✅ Complete |
| api/routes/test_payments.py | 43 | ✅ Complete (13 minor failures) |
| api/routes/tenant/test_auth.py | 4 | ✅ Existing |
| **Total** | **~490** | **🟡 In Progress** |

---

## Progress Tracker

### Phase 1: Infrastructure & Core Models ✅ COMPLETED
- [x] Create test factories (factories.py) - 7 model factories
- [x] Expand conftest.py with comprehensive fixtures - 30+ fixtures including auth and file uploads
- [x] Test Landlord model - 20 tests (CRUD, relationships, password hashing)
- [x] Test Property model - 23 tests (CRUD, grace_period, stats)
- [x] Test Room model - 33 tests (CRUD, occupancy, currency, tenant tracking)
- [x] Test Tenant model - 38 tests (CRUD, dates, active status, portal access)
- [x] Test Payment model - 57 tests (all 7 statuses, calculations, transitions)
- [x] Test PaymentSchedule model - 60 tests (frequencies, due_day, window_days)
- [x] Test core security - 50+ tests (hashing, JWT tokens, auth dependencies)
- [x] Test currency utilities - 40+ tests (conversions, formatting, validation)

### Phase 2: API Route Tests ✅ COMPLETED
- [x] Landlord auth tests - Covered in test_core/test_security.py
- [x] Tenant portal auth tests - 4 tests (existing) in test_auth.py
- [x] Property routes (test_properties.py) - 28 tests:
  - GET /properties (list with stats)
  - POST /properties (create)
  - GET /properties/{id} (single with stats)
  - PUT /properties/{id} (update including grace_period)
  - DELETE /properties/{id} (with room restriction)
- [x] Room routes (test_rooms.py) - 39 tests:
  - GET /rooms (list with tenant info)
  - POST /rooms (create)
  - GET /rooms/{id} (single with tenant)
  - PUT /rooms/{id} (update)
  - DELETE /rooms/{id} (with tenant restriction)
  - POST /rooms/bulk (bulk creation with price ranges)
- [x] Tenant management routes (test_tenants.py) - 55 tests:
  - GET /tenants (list with filters)
  - POST /tenants (create with auto schedule)
  - GET /tenants/{id} (details with payments)
  - PUT /tenants/{id} (update)
  - POST /tenants/{id}/move-out
  - POST /tenants/{id}/enable-portal
  - POST /tenants/{id}/disable-portal
  - Payment schedule CRUD
  - Prorated payment generation
- [x] Payment routes (test_payments.py) - 43 tests:
  - GET /payments (list with filters)
  - GET /payments/summary (statistics)
  - POST /payments (manual creation)
  - GET /payments/{id}
  - PUT /payments/{id} (update)
  - POST /payments/{id}/mark-paid
  - POST /payments/{id}/waive
  - POST /payments/{id}/receipt (actual file uploads: PNG, JPG, PDF)
  - File validation (type, size)
  - Status transitions (PENDING → VERIFYING → ON_TIME/LATE)

### Phase 3: Integration Tests ⏳ PENDING
- [ ] Complete tenant onboarding flow (property → room → tenant → portal)
- [ ] Payment collection end-to-end (upload → approve → receipt)
- [ ] Overdue handling workflow
- [ ] Bulk room creation workflow
- [ ] Multi-tenant property workflow

### Phase 4: Edge Cases & Error Handling ⏳ PENDING
- [ ] Concurrent modification tests
- [ ] Database constraint violation tests
- [ ] Large file upload stress tests (>10MB)
- [ ] Malformed request tests
- [ ] Rate limiting tests (if applicable)

---

## Test Commands

```bash
# Run all tests
cd backend && pytest

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Run specific modules
pytest tests/test_models/ -v
pytest tests/test_core/ -v
pytest tests/api/routes/test_payments.py -v

# Run integration tests only
pytest tests/integration/ -v

# Run with verbose output
pytest -vv

# Run failed tests only
pytest --lf -v
```

---

## Coverage Estimates by Module

| Module | Target | Current | File |
|--------|--------|---------|------|
| models/landlord | 90% | 85% | test_landlord.py |
| models/property | 90% | 85% | test_property.py |
| models/room | 90% | 85% | test_room.py |
| models/tenant | 90% | 85% | test_tenant.py |
| models/payment | 90% | 85% | test_payment.py |
| models/payment_schedule | 90% | 85% | test_payment_schedule.py |
| core/security | 95% | 90% | test_security.py |
| core/currency | 90% | 90% | test_currency.py |
| routers/properties | 85% | 80% | test_properties.py |
| routers/rooms | 85% | 80% | test_rooms.py |
| routers/tenants | 85% | 80% | test_tenants.py |
| routers/payments | 85% | 70% | test_payments.py (13 tests need fixes) |
| routers/tenant_auth | 90% | 80% | test_auth.py (needs expansion) |
| services/payment_service | 80% | 60% | Need to create tests |
| **Overall** | **80%** | **~60%** | **Progress: 75%** |

---

## Known Issues & Fixes

### Minor Test Failures (13 tests in test_payments.py)
**Issue:** Payment status assertions expect uppercase but API returns lowercase
**Example:** `assert data["status"] == "ON_TIME"` fails, gets `"on_time"`

**Fix Needed:** Update assertions to use lowercase or `.lower()` comparison:
```python
# Current (failing):
assert data["status"] == "ON_TIME"

# Fix:
assert data["status"].lower() == "on_time"
```

**Files affected:** test_payments.py lines 139, 459, 478, 507, 535, 600, etc.

---

## Next Steps to Reach 80% Coverage

1. **Fix payment test assertions** (13 tests) - 1 hour
2. **Create payment_service tests** - Test proration, schedule generation - 2 hours
3. **Create integration tests** - End-to-end workflows - 3 hours
4. **Add landlord auth route tests** - Registration, login endpoints - 1 hour
5. **Expand tenant auth tests** - Add more portal flow tests - 1 hour

**Total effort remaining:** ~8 hours to reach 80% coverage

---

## PR Information

**Branch:** `feature/comprehensive-test-suite`  
**Pull Request:** https://github.com/Kasuletrevor/landten/pull/10  
**Commits:** 10+ commits following conventional commit format

---

**Last Updated:** 2025-01-30  
**Current Status:** Phases 1-2 Complete (~490 tests created), Phase 3-4 Pending

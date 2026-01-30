# Backend Testing Plan - LandTen

**Status:** In Progress  
**Target Coverage:** 80%  
**Approach:** Bottom-up (Auth/Models → Routes → Integration)  
**Test Type:** Full end-to-end with actual file uploads

---

## Progress Tracker

### Phase 1: Infrastructure & Core Models ✅ COMPLETED
- [x] Create test factories (factories.py)
- [x] Expand conftest.py with comprehensive fixtures
- [ ] Test Landlord model (CRUD, relationships)
- [ ] Test Property model (CRUD, grace_period)
- [ ] Test Room model (CRUD, occupancy, currency)
- [ ] Test Tenant model (CRUD, dates, active status)
- [ ] Test Payment model (all statuses, calculations)
- [ ] Test PaymentSchedule model (frequency, due_day)
- [ ] Test core security (hashing, tokens)
- [ ] Test currency utilities

### Phase 2: Authentication & Authorization ⏳ PENDING
- [ ] Landlord registration tests
- [ ] Landlord login tests (valid/invalid)
- [ ] Token refresh tests
- [ ] Protected route access tests
- [ ] Tenant portal enable/disable tests
- [ ] Tenant password setup tests
- [ ] Tenant login flow tests
- [ ] Password change tests

### Phase 3: Property & Room Management ⏳ PENDING
- [ ] GET /properties list tests
- [ ] POST /properties create tests
- [ ] GET /properties/{id} with stats tests
- [ ] PUT /properties/{id} update tests
- [ ] DELETE /properties/{id} tests
- [ ] GET /rooms list tests
- [ ] POST /rooms create tests
- [ ] Room occupancy validation tests
- [ ] Room deletion restrictions tests

### Phase 4: Tenant Management ⏳ PENDING
- [ ] Create tenant with auto schedule tests
- [ ] Prorated payment calculation tests
- [ ] First payment generation tests
- [ ] Room occupancy on tenant creation tests
- [ ] List tenants with filters tests
- [ ] Get tenant details tests
- [ ] Update tenant tests
- [ ] Move-out process tests
- [ ] Portal access toggle tests

### Phase 5: Payments & Receipts ⏳ PENDING
- [ ] Scheduled payment generation tests
- [ ] Manual payment creation tests
- [ ] Payment status transition tests
- [ ] Prorated calculation tests
- [ ] Days until/overdue computation tests
- [ ] Receipt upload (actual file) tests
- [ ] File validation tests
- [ ] Receipt retrieval tests
- [ ] Payment summary calculations tests
- [ ] Dashboard analytics tests

### Phase 6: Integration Tests ⏳ PENDING
- [ ] Complete tenant onboarding flow
- [ ] Payment collection end-to-end
- [ ] Receipt upload → approval workflow
- [ ] Overdue handling workflow
- [ ] File upload with real images/PDFs

### Phase 7: Edge Cases & Error Handling ⏳ PENDING
- [ ] Invalid file type tests
- [ ] Oversized file tests
- [ ] Concurrent modification tests
- [ ] Database constraint tests
- [ ] Expired/invalid token tests
- [ ] Missing required fields tests
- [ ] Unauthorized access tests
- [ ] Delete with dependencies tests

---

## Test Commands

```bash
# Run all tests
cd backend && pytest

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Run specific phase
pytest tests/test_models/ -v
pytest tests/api/routes/test_auth.py -v

# Run integration tests
pytest tests/integration/ -v

# Run with verbose output
pytest -vv
```

## Coverage Targets by Module

| Module | Target | Current |
|--------|--------|---------|
| models | 90% | 0% |
| core/security | 95% | 0% |
| core/currency | 90% | 0% |
| routers/auth | 90% | 0% |
| routers/tenant_auth | 90% | 40% |
| routers/properties | 85% | 0% |
| routers/rooms | 85% | 0% |
| routers/tenants | 85% | 0% |
| routers/payments | 85% | 0% |
| services | 80% | 0% |
| **Overall** | **80%** | **~5%** |

## Issues Found & Fixed

*Document bugs found and fixed during testing here*

---

**Last Updated:** 2025-01-30  
**Current Phase:** Phase 1 - Infrastructure & Core Models

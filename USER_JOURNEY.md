# LandTen User Journey Map

## Overview

LandTen is a landlord-tenant management platform built around manual rent
verification. Tenants pay by bank transfer, upload proof of payment, and
landlords review the receipt before the payment is accepted.

## Primary Personas

### Landlord

#### Landlord goals

- Manage multiple properties and rooms efficiently
- Track rent payments and reduce delinquency
- Keep tenant records organized
- Export data for reporting and accounting
- Communicate with tenants without scattered spreadsheets and phone follow-up

#### Landlord pain points

- Manual payment tracking in spreadsheets
- Poor visibility into overdue rent and tenant history
- Slow receipt verification
- Weak audit trail when disputes happen

### Tenant

#### Tenant goals

- View rent status and payment history
- Upload receipts quickly after transfer
- Receive reminders before and after due dates
- Track what the landlord has approved or rejected
- Report maintenance issues and follow progress

#### Tenant pain points

- Uncertainty about whether a payment was accepted
- No clear place to upload payment proof
- Limited access to historical payment records
- Weak communication loop with the landlord

## Phase 1: Onboarding and Setup

### Landlord onboarding

#### 1. Account creation

**Entry point:** landing page (`/`)

```text
1. Visit LandTen
2. Click "Get Started" or "Sign Up"
3. Fill registration form:
   - Name
   - Email
   - Password
   - Phone
4. Submit -> account created
5. Redirect to dashboard
```

**Emotional state:** curious -> hopeful

#### 2. First property setup

**Entry point:** empty landlord dashboard

```text
1. See empty state call to action
2. Click "Add Your First Property"
3. Enter:
   - Property name
   - Address
   - Description
   - Grace period days
4. Submit -> property created
5. Move to room setup
```

**Emotional state:** excited -> accomplished

#### 3. Room configuration

**Entry point:** property detail page

```text
1. Click "Add Room"
2. Create one room or use bulk creation
3. Enter:
   - Room name or number
   - Rent amount
   - Currency
4. Save rooms
5. Review occupancy state
```

**Emotional state:** productive -> organized

#### 4. First tenant onboarding

**Entry point:** rooms list

```text
1. Click "Add Tenant" on a vacant room
2. Enter:
   - Name
   - Email
   - Phone
   - Move-in date
   - Notes
3. System prepares payment schedule
4. Optionally enable portal access
5. Tenant receives invite email
```

**Emotional state:** professional -> in control

### Tenant onboarding

#### 5. Portal setup

**Entry point:** invite email

```text
1. Open invite email
2. Click setup link
3. Review tenancy details
4. Set password
5. Activate portal account
6. Redirect to tenant dashboard
```

**Emotional state:** surprised -> reassured

#### 6. First login

**Entry point:** `/tenant/login`

```text
1. Open tenant login
2. Enter email and password
3. Load tenant dashboard
4. Review room, property, and payment state
```

**Emotional state:** curious -> confident

## Phase 2: Daily Operations

### Landlord daily workflow

#### 7. Dashboard review

**Entry point:** `/dashboard`

```text
1. Log in
2. Review outstanding rent, overdue count, and trends
3. Check notifications
4. Inspect active maintenance requests
```

**Emotional state:** informed -> proactive

#### 8. Payment monitoring

**Entry point:** `/dashboard/payments`

```text
1. View all payments
2. Filter by property, status, or date
3. Identify overdue and verifying payments
4. Send reminders or open dispute threads
5. Export payment data when needed
```

**Emotional state:** vigilant -> responsive

#### 9. Receipt verification

**Entry point:** payment row with `VERIFYING` status

```text
1. Open uploaded receipt
2. Review the transfer proof
3. Choose:
   - Approve -> mark paid
   - Reject -> return to pending or overdue
4. Tenant receives update
```

**Emotional state:** evaluative -> decisive

#### 10. Tenant lifecycle management

**Entry point:** `/dashboard/tenants`

```text
1. Add new tenants to vacant rooms
2. Update tenant records
3. Process move-out when tenancy ends
4. Keep room availability accurate
```

**Emotional state:** systematic -> complete

### Tenant daily workflow

#### 11. Payment status checking

**Entry point:** `/tenant/dashboard`

```text
1. Log in
2. Review next due amount and due date
3. Check history and any rejected receipts
4. Confirm whether action is needed
```

**Emotional state:** aware -> prepared

#### 12. Receipt upload

**Entry point:** actionable payment card

```text
1. Make bank transfer
2. Click "Upload Receipt"
3. Select image or PDF
4. Submit receipt
5. Status moves to VERIFYING
6. Wait for landlord decision
```

**Emotional state:** proactive -> waiting

#### 13. Rejection and re-upload flow

**Entry point:** rejected receipt state on tenant dashboard

```text
1. View rejection reason
2. Understand what was wrong
3. Upload corrected receipt
4. Return payment to verification flow
```

**Emotional state:** frustrated -> reassured

#### 14. Maintenance reporting

**Entry point:** tenant maintenance section

```text
1. Click "Report Issue"
2. Enter:
   - Category
   - Urgency
   - Title
   - Description
   - Preferred entry time
3. Submit request
4. Follow comments and status updates
5. Resolve or reopen when work is completed
```

**Emotional state:** concerned -> hopeful

## Phase 3: Communication and Support

### Payment reminders

#### Landlord flow

```text
1. Find overdue payment
2. Click "Send Reminder"
3. System sends email reminder
4. Reminder is logged for landlord visibility
```

#### Tenant effect

```text
1. Receive reminder email
2. Review amount and due context
3. Pay or respond through the product if there is a discrepancy
```

### Payment dispute thread

#### Payment dispute flow

```text
1. One side opens a dispute
2. Both sides exchange messages
3. Optional attachments are added
4. Thread stays open until resolved
5. Resolution or reopen state is visible to both parties
```

### Maintenance communication

#### Maintenance flow

```text
1. Tenant submits maintenance request
2. Landlord acknowledges and updates status
3. Both sides add comments or attachments
4. Tenant closes the loop with rating or feedback
```

## Phase 4: Reporting and Analysis

### Landlord monthly review

**Entry point:** dashboard and payments pages

```text
1. Review collection totals and overdue trend
2. Inspect vacancy and active maintenance load
3. Export filtered payment data
4. Prepare records for accounting or tax work
```

**Emotional state:** analytical -> strategic

## Crisis Management Flow

### Delinquency path

```text
Due date arrives -> payment remains pending
Grace period passes -> payment becomes overdue
Landlord sends reminder -> tenant responds
Tenant uploads proof or explains discrepancy
Landlord approves, rejects, waives, or negotiates offline
```

#### Landlord actions

- Send reminders
- Review uploaded proof
- Reject with a clear reason when needed
- Track the audit trail

#### Tenant actions

- Upload proof quickly
- Re-upload when rejected
- Use dispute thread for discrepancies

## Critical User Flows

### Flow 1: First payment cycle

```text
Move-in -> schedule created -> due date arrives ->
tenant uploads receipt -> landlord approves -> payment complete
```

#### Flow 1 success metrics

- Time from move-in to first completed payment under 30 days
- Receipt approval turnaround under 48 hours
- Tenant portal adoption above 80 percent

### Flow 2: Monthly rent collection

```text
Due date -> bank transfer -> receipt upload ->
verification -> payment history updated
```

#### Flow 2 success metrics

- On-time payment rate above 90 percent
- Receipt upload compliance above 95 percent
- Verification turnaround under 24 hours

### Flow 3: Delinquency recovery

```text
Payment overdue -> reminder sent -> tenant responds ->
receipt uploaded or discrepancy discussed -> issue resolved
```

#### Flow 3 success metrics

- Recovery rate above 75 percent
- Time to recovery under 7 days
- Escalation rate below 5 percent

## Current Implementation Status

### Completed

- Landlord authentication and dashboard
- Property, room, and tenant management
- Payment schedules and payment tracking
- Tenant receipt upload
- Landlord receipt approval and rejection
- Tenant portal and tenant dashboard
- Payment dispute threads with attachments
- Maintenance requests and comments
- Basic SSE notifications and email updates
- Dashboard analytics and payment exports

### Needs polish

- Full outbound email credential setup for deployment
- Production SMS integration
- End-to-end deployment smoke testing with Docker daemon running locally

### Future enhancements

- Lease document lifecycle polish
- Persistent offline notification inbox for tenants
- Richer reporting and accounting exports
- Real SMS or WhatsApp delivery
- Advanced settings and automation rules

## Recommendations

### Immediate priority

1. Rotate and configure real email credentials
2. Stabilize deployment with full container smoke testing
3. Persist tenant-facing notifications beyond SSE

### Short-term priority

1. Integrate a real SMS provider
2. Expand reporting and export coverage
3. Improve admin settings and operational controls

### Long-term priority

1. Add deeper accounting integrations
2. Add mobile-first communication channels
3. Add more automation around delinquency and maintenance workflows

*This journey map reflects the current product shape after the payment,
maintenance, auth, deployment, and PostgreSQL hardening work.*

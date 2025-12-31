# LandTen - Landlord-Tenant Management Platform

A full-stack property management system for landlords to manage properties, rooms, tenants, and payment tracking. Includes a tenant portal for tenants to view their payment history and upload proof of payment receipts.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Payment Flow](#payment-flow)
- [Database Schema](#database-schema)
- [Environment Variables](#environment-variables)
- [Development Notes](#development-notes)

---

## Overview

LandTen is designed for landlords who manage rental properties and need to:

1. Track properties and rooms
2. Manage tenant information and lease periods
3. Automate payment schedule generation
4. Track payment statuses (upcoming, pending, overdue, paid)
5. Receive notifications for payment events
6. Allow tenants to upload proof of payment for manual verification

The system explicitly does NOT integrate with payment gateways (e.g., Stripe). Instead, it follows a manual verification workflow where tenants upload bank transfer receipts and landlords approve payments.

---

## Architecture

```
landten/
├── backend/          # FastAPI + SQLModel + SQLite
│   ├── app/
│   │   ├── core/     # Config, database, security
│   │   ├── models/   # SQLModel database models
│   │   ├── routers/  # API endpoints
│   │   ├── schemas/  # Pydantic request/response schemas
│   │   └── services/ # Business logic (payments, notifications)
│   ├── alembic/      # Database migrations
│   └── tests/        # Pytest test suite
│
└── frontend/         # Next.js 14 (App Router)
    └── src/
        ├── app/      # Pages and layouts
        │   ├── dashboard/    # Landlord dashboard
        │   └── tenant/       # Tenant portal
        ├── components/       # Shared UI components
        └── lib/              # API client, auth context
```

---

## Features

### Landlord Dashboard

- **Properties**: Create, update, delete properties with address information
- **Rooms**: Manage rooms within properties, set rent amounts
- **Tenants**: Add tenants to rooms, track move-in/move-out dates
- **Payment Schedules**: Configure recurring payment schedules (monthly, bi-monthly, quarterly)
- **Payment Tracking**: View all payments, filter by status, mark as paid or waived
- **Notifications**: Real-time SSE notifications for payment events
- **Tenant Portal Management**: Enable/disable tenant portal access, generate invite links

### Tenant Portal

- **Dashboard**: View tenancy details, property info, payment summary
- **Payment History**: See all past and upcoming payments with status
- **Receipt Upload**: Upload proof of payment (JPG, PNG, PDF) for pending payments
- **Account Setup**: Set password via invite link from landlord

### Payment System

- **Automatic Generation**: Background scheduler generates payment records based on schedules
- **Status Tracking**: UPCOMING -> PENDING -> (ON_TIME | LATE | OVERDUE | WAIVED | VERIFYING)
- **Grace Window**: Configurable payment window (e.g., 5 days after due date)
- **Manual Payments**: Landlords can create one-off charges outside regular schedules

---

## Tech Stack

### Backend

| Component | Technology |
|-----------|------------|
| Framework | FastAPI 0.109.2 |
| ORM | SQLModel 0.0.14 (SQLAlchemy + Pydantic) |
| Database | SQLite (development) |
| Migrations | Alembic 1.13.1 |
| Auth | JWT (python-jose) + bcrypt |
| Scheduler | APScheduler 3.10.4 |
| Email | aiosmtplib |

### Frontend

| Component | Technology |
|-----------|------------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS + Custom CSS Variables |
| Icons | Lucide React |
| State | React Context API |
| HTTP | Fetch API |

---

## Project Structure

### Backend

```
backend/
├── alembic/
│   └── versions/           # Migration files
├── app/
│   ├── core/
│   │   ├── config.py       # Settings from environment
│   │   ├── database.py     # SQLite engine setup
│   │   └── security.py     # JWT creation/validation, password hashing
│   ├── models/
│   │   ├── landlord.py     # Landlord account model
│   │   ├── property.py     # Property model
│   │   ├── room.py         # Room model
│   │   ├── tenant.py       # Tenant model with portal access
│   │   ├── payment_schedule.py  # Recurring payment configuration
│   │   ├── payment.py      # Individual payment records
│   │   └── notification.py # Notification model
│   ├── routers/
│   │   ├── auth.py         # Landlord authentication
│   │   ├── tenant_auth.py  # Tenant portal authentication
│   │   ├── properties.py   # Property CRUD
│   │   ├── rooms.py        # Room CRUD
│   │   ├── tenants.py      # Tenant management
│   │   ├── payments.py     # Payment operations + receipt upload
│   │   └── notifications.py # Notification endpoints + SSE
│   ├── schemas/            # Pydantic models for API
│   ├── services/
│   │   ├── payment_service.py      # Payment generation logic
│   │   ├── notification_service.py # Notification creation
│   │   ├── email_service.py        # Email sending
│   │   └── sms_service.py          # SMS sending (stub)
│   └── main.py             # FastAPI app entry point
├── uploads/
│   └── receipts/           # Uploaded receipt files
├── tests/
│   └── api/routes/tenant/  # Tenant auth tests
├── alembic.ini
└── requirements.txt
```

### Frontend

```
frontend/
├── src/
│   ├── app/
│   │   ├── dashboard/
│   │   │   ├── payments/page.tsx
│   │   │   ├── properties/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── tenants/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── tenant/
│   │   │   ├── dashboard/
│   │   │   │   ├── page.tsx
│   │   │   │   └── ReceiptUploadModal.tsx
│   │   │   ├── login/page.tsx
│   │   │   └── setup/page.tsx
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   └── toast-provider.tsx
│   └── lib/
│       ├── api.ts          # API client with all endpoints
│       └── auth-context.tsx # Authentication state management
├── package.json
└── tsconfig.json
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with docs at `/docs`.

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

---

## API Documentation

Once the backend is running, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register landlord account |
| POST | /api/auth/login | Landlord login |
| GET | /api/properties | List all properties |
| POST | /api/properties | Create property |
| GET | /api/tenants | List all tenants |
| POST | /api/tenants | Create tenant |
| POST | /api/tenants/{id}/enable-portal | Generate tenant invite link |
| GET | /api/payments | List payments with filters |
| PUT | /api/payments/{id}/mark-paid | Mark payment as paid |
| POST | /api/payments/{id}/upload-receipt | Tenant uploads receipt |
| POST | /api/tenant-auth/login | Tenant portal login |
| POST | /api/tenant-auth/setup-password | Tenant sets password from invite |
| GET | /api/tenant-auth/payments | Tenant views their payments |

---

## Payment Flow

### 1. Payment Generation (Automatic)

The system runs a daily scheduler at 1:00 AM that:

1. Updates payment statuses based on current date
2. Generates new payment records for active schedules

### 2. Payment Status Lifecycle

```
UPCOMING  ->  PENDING  ->  ON_TIME (if paid in window)
                      ->  LATE (if paid after window)
                      ->  OVERDUE (if not paid)
                      ->  WAIVED (if forgiven by landlord)
                      ->  VERIFYING (if tenant uploaded receipt)
```

### 3. Manual Verification Workflow

1. Tenant sees pending payment in portal
2. Tenant clicks "Upload Receipt" and submits bank transfer proof
3. Payment status changes to VERIFYING
4. Landlord reviews receipt in dashboard
5. Landlord marks as ON_TIME/LATE or rejects (returns to PENDING)

---

## Database Schema

### Core Models

**Landlord**
- id, email, password_hash, name, phone, created_at

**Property**
- id, landlord_id, name, address, description, timestamps

**Room**
- id, property_id, name, rent_amount, is_occupied, timestamps

**Tenant**
- id, room_id, name, email, phone, move_in_date, move_out_date
- has_portal_access, invite_token, password_hash, timestamps

**PaymentSchedule**
- id, tenant_id, amount, frequency, due_day, window_days
- start_date, is_active, timestamps

**Payment**
- id, tenant_id, schedule_id, period_start, period_end
- amount_due, due_date, window_end_date, status
- paid_date, payment_reference, receipt_url, notes
- is_manual, timestamps

**Notification**
- id, landlord_id, type, title, message, is_read
- payment_id, tenant_id, created_at

---

## Environment Variables

### Backend (.env)

```env
# Application
APP_NAME=LandTen
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=sqlite:///./landten.db

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000

# Email (optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password
EMAIL_FROM=noreply@example.com
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## Development Notes

### Important Decisions

1. **No Payment Gateway Integration**: The system uses manual bank transfer verification. Tenants upload receipts, landlords verify. This was a deliberate decision to avoid Stripe/payment processor complexity.

2. **SQLite for Development**: Simple setup, no external database server required. Consider PostgreSQL for production.

3. **File Storage**: Receipts are stored locally in `backend/uploads/receipts/`. For production, consider S3 or similar cloud storage.

4. **Dual Authentication**: Landlords and tenants have separate auth flows. Tenants must be invited by landlords and set up their password via a one-time token.

### Known Limitations

- No multi-tenancy (single landlord per property currently works, but schema supports expansion)
- Receipt files stored locally (not suitable for distributed deployment)
- SMS service is a stub (requires Twilio or similar integration)
- No payment rejection workflow yet (landlord can only approve)

### Future Enhancements

- Landlord view for verifying receipts with approve/reject actions
- Payment rejection with notes sent back to tenant
- Cloud storage integration for receipts
- Email notifications when payment status changes
- Mobile-responsive improvements
- Multi-currency support

---

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v
```

### Running Specific Tests

```bash
pytest tests/api/routes/tenant/test_auth.py -v
```

---

## License

This project is proprietary software. All rights reserved.

---

## Contributing

Please see AGENTS.md for development guidelines and workflow conventions.

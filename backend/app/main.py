"""
LandTen - Landlord-Tenant Management Platform
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session

from app.core.config import settings
from app.core.database import engine
from app.routers import (
    auth,
    properties,
    rooms,
    tenants,
    payments,
    notifications,
    tenant_auth,
)
from app.services.payment_service import (
    generate_all_due_payments,
    update_payment_statuses,
)

# Background scheduler
scheduler = AsyncIOScheduler()


def run_daily_payment_tasks():
    """
    Run daily payment tasks:
    1. Update payment statuses (upcoming -> pending -> overdue)
    2. Generate new payment periods for schedules that need them
    """
    with Session(engine) as session:
        # Update existing payment statuses
        updated = update_payment_statuses(session)
        if updated:
            print(f"[Scheduler] Updated {updated} payment statuses")

        # Generate new payments
        generated = generate_all_due_payments(session)
        if generated:
            print(f"[Scheduler] Generated {len(generated)} new payments")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Startup: Initialize scheduler for background tasks.
    Shutdown: Clean up scheduler.
    """
    # Startup
    print(f"Starting {settings.APP_NAME} API...")

    # Run payment tasks immediately on startup
    run_daily_payment_tasks()

    # Schedule daily tasks at 1:00 AM
    scheduler.add_job(
        run_daily_payment_tasks,
        trigger=CronTrigger(hour=1, minute=0),
        id="daily_payment_tasks",
        name="Daily Payment Status Updates and Generation",
        replace_existing=True,
    )
    scheduler.start()
    print("[Scheduler] Background scheduler started")

    yield

    # Shutdown
    scheduler.shutdown()
    print("[Scheduler] Background scheduler stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Landlord-Tenant Management Platform - Payment Reconciliation & Tracking",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(tenant_auth.router, prefix="/api")
app.include_router(properties.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(tenants.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "name": settings.APP_NAME,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}

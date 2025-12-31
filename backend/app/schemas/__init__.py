# Export all schemas
from app.schemas.landlord import (
    LandlordCreate,
    LandlordUpdate,
    LandlordLogin,
    LandlordResponse,
    TokenResponse,
    LoginResponse,
)
from app.schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyWithStats,
    PropertyListResponse,
)
from app.schemas.room import (
    RoomCreate,
    RoomUpdate,
    RoomResponse,
    RoomWithTenant,
    RoomListResponse,
)
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantMoveOut,
    TenantResponse,
    TenantWithDetails,
    TenantListResponse,
)
from app.schemas.payment_schedule import (
    PaymentScheduleCreate,
    PaymentScheduleUpdate,
    PaymentScheduleResponse,
)
from app.schemas.payment import (
    PaymentMarkPaid,
    PaymentWaive,
    PaymentUpdate,
    ManualPaymentCreate,
    PaymentResponse,
    PaymentWithTenant,
    PaymentListResponse,
    PaymentSummary,
)
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    SSEEvent,
)
from app.schemas.common import APIResponse, APIError

__all__ = [
    # Landlord
    "LandlordCreate",
    "LandlordUpdate",
    "LandlordLogin",
    "LandlordResponse",
    "TokenResponse",
    "LoginResponse",
    # Property
    "PropertyCreate",
    "PropertyUpdate",
    "PropertyResponse",
    "PropertyWithStats",
    "PropertyListResponse",
    # Room
    "RoomCreate",
    "RoomUpdate",
    "RoomResponse",
    "RoomWithTenant",
    "RoomListResponse",
    # Tenant
    "TenantCreate",
    "TenantUpdate",
    "TenantMoveOut",
    "TenantResponse",
    "TenantWithDetails",
    "TenantListResponse",
    # Payment Schedule
    "PaymentScheduleCreate",
    "PaymentScheduleUpdate",
    "PaymentScheduleResponse",
    # Payment
    "PaymentMarkPaid",
    "PaymentWaive",
    "PaymentUpdate",
    "ManualPaymentCreate",
    "PaymentResponse",
    "PaymentWithTenant",
    "PaymentListResponse",
    "PaymentSummary",
    # Notification
    "NotificationResponse",
    "NotificationListResponse",
    "SSEEvent",
    # Common
    "APIResponse",
    "APIError",
]

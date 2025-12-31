"""
Rate limiting configuration using slowapi.
Protects authentication endpoints from brute force attacks.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    Handles proxied requests by checking X-Forwarded-For header.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(key_func=get_client_ip)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    Returns a JSON response with appropriate error message.
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many login attempts. Please try again later.",
            "retry_after": exc.detail,
        },
    )


# Rate limit configurations
# Login endpoints: 5 attempts per minute per IP
AUTH_RATE_LIMIT = "5/minute"

# Password setup: 3 attempts per minute (more restrictive)
SETUP_RATE_LIMIT = "3/minute"

# General API: 100 requests per minute
API_RATE_LIMIT = "100/minute"

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlmodel import Session, select
from datetime import timedelta

from app.core.database import get_session
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_landlord,
    AUTH_COOKIE_NAME,
)
from app.core.config import settings
from app.core.rate_limit import limiter, AUTH_RATE_LIMIT
from app.models.landlord import Landlord
from app.schemas.landlord import (
    LandlordCreate,
    LandlordLogin,
    LandlordResponse,
    LoginResponse,
    LandlordUpdate,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.FRONTEND_URL.startswith("https://"),
        samesite="lax",
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        secure=settings.FRONTEND_URL.startswith("https://"),
        httponly=True,
        samesite="lax",
    )


@router.post(
    "/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    landlord_data: LandlordCreate,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    Register a new landlord account.
    Returns access token and landlord info on success.
    """
    # Check if email already exists
    statement = select(Landlord).where(Landlord.email == landlord_data.email)
    existing = session.exec(statement).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new landlord
    landlord = Landlord(
        email=landlord_data.email,
        password_hash=get_password_hash(landlord_data.password),
        name=landlord_data.name,
        phone=landlord_data.phone,
    )
    session.add(landlord)
    session.commit()
    session.refresh(landlord)

    # Create access token
    access_token = create_access_token(
        data={"sub": landlord.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    _set_auth_cookie(response, access_token)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        landlord=LandlordResponse.model_validate(landlord),
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request,
    credentials: LandlordLogin,
    response: Response,
    session: Session = Depends(get_session),
):
    """
    Login with email and password.
    Returns access token and landlord info on success.
    Rate limited to 5 attempts per minute per IP.
    """
    # Find landlord by email
    statement = select(Landlord).where(Landlord.email == credentials.email)
    landlord = session.exec(statement).first()

    if not landlord or not verify_password(
        credentials.password, landlord.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": landlord.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    _set_auth_cookie(response, access_token)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        landlord=LandlordResponse.model_validate(landlord),
    )


@router.get("/me", response_model=LandlordResponse)
async def get_me(current_landlord: Landlord = Depends(get_current_landlord)):
    """
    Get current authenticated landlord's profile.
    """
    return LandlordResponse.model_validate(current_landlord)


@router.put("/me", response_model=LandlordResponse)
async def update_me(
    update_data: LandlordUpdate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Update current landlord's profile.
    """
    if update_data.name is not None:
        current_landlord.name = update_data.name
    if update_data.phone is not None:
        current_landlord.phone = update_data.phone

    session.add(current_landlord)
    session.commit()
    session.refresh(current_landlord)

    return LandlordResponse.model_validate(current_landlord)


@router.post("/logout")
async def logout(
    response: Response,
    current_landlord: Landlord = Depends(get_current_landlord),
):
    """
    Logout current landlord by clearing auth cookie.
    """
    _ = current_landlord
    _clear_auth_cookie(response)
    return {"message": "Logged out"}

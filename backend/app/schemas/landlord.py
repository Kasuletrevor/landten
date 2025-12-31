from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# Request schemas
class LandlordCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None


class LandlordUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class LandlordLogin(BaseModel):
    email: EmailStr
    password: str


# Response schemas
class LandlordResponse(BaseModel):
    id: str
    email: str
    name: str
    phone: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    landlord: LandlordResponse

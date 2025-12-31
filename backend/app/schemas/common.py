from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper"""

    data: Optional[T] = None
    message: str = "Success"


class APIError(BaseModel):
    """Standard error response"""

    error: str
    detail: Optional[str] = None

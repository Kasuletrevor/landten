"""
Schemas for payment export functionality.
"""

from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import date
from enum import Enum


class ExportFormat(str, Enum):
    """Supported export formats."""

    EXCEL = "excel"
    PDF = "pdf"


class ExportRequest(BaseModel):
    """Request parameters for payment export."""

    format: ExportFormat
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    property_id: Optional[str] = None
    tenant_id: Optional[str] = None
    status: Optional[str] = None

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, end_date, info):
        """Validate that date range doesn't exceed 2 years."""
        start_date = info.data.get("start_date")
        if start_date and end_date:
            # Calculate difference in days
            delta = (end_date - start_date).days
            if delta > 730:  # 2 years
                raise ValueError("Date range cannot exceed 2 years")
            if delta < 0:
                raise ValueError("End date must be after start date")
        return end_date

    @model_validator(mode="after")
    def set_default_dates(self):
        """Set default date range to current year if not provided."""
        if not self.start_date:
            self.start_date = date(date.today().year, 1, 1)
        if not self.end_date:
            self.end_date = date(date.today().year, 12, 31)
        return self


class ExportResponse(BaseModel):
    """Response after initiating export."""

    filename: str
    content_type: str
    size_bytes: int
    record_count: int

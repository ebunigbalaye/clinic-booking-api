from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SlotCreate(BaseModel):
    id: str
    provider: str
    start_time: datetime
    end_time: datetime

    model_config = ConfigDict(extra="forbid")

    @field_validator("start_time", "end_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must include a timezone")
        return value


class ResetRequest(BaseModel):
    slots: list[SlotCreate]

    model_config = ConfigDict(extra="forbid")


class SlotResponse(BaseModel):
    id: str
    provider: str
    start_time: datetime
    end_time: datetime
    available: bool


class SlotsResponse(BaseModel):
    slots: list[SlotResponse]


class ResetResponse(BaseModel):
    message: str


class BookingCreate(BaseModel):
    slot_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: EmailStr

    model_config = ConfigDict(extra="forbid")

    @field_validator("slot_id", "name", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value


class BookingResponse(BaseModel):
    id: str
    slot_id: str
    name: str
    email: str
    status: Literal["confirmed", "cancelled"]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingPageResponse(BaseModel):
    bookings: list[BookingResponse]
    next_cursor: str | None

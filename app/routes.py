import base64
import binascii
import hashlib
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import EmailStr
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Slot
from app.rate_limit import enforce_booking_rate_limit
from app.schemas import (
    BookingCreate,
    BookingPageResponse,
    BookingResponse,
    ResetRequest,
    ResetResponse,
    SlotsResponse,
)

router = APIRouter()



def encode_cursor(booking: Booking) -> str:
    cursor_data = {
        "created_at": booking.created_at.isoformat(),
        "id": booking.id,
    }
    encoded = base64.urlsafe_b64encode(json.dumps(cursor_data).encode("utf-8"))

    return encoded.decode("utf-8").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded_cursor = cursor + "=" * (-len(cursor) % 4)

        decoded = base64.b64decode(
            padded_cursor,
            altchars=b"-_",
            validate=True,
        )

        data = json.loads(decoded.decode("utf-8"))

        created_at = datetime.fromisoformat(data["created_at"])
        booking_id = data["id"]

        if (
            created_at.tzinfo is None
            or created_at.utcoffset() is None
            or not isinstance(booking_id, str)
            or not booking_id
        ):
            raise ValueError

        return created_at, booking_id

    except (
        ValueError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ):
        raise HTTPException(
            status_code=400,
            detail="invalid cursor",
        )


@router.post("/reset", response_model=ResetResponse)
def reset_slots(
    request: ResetRequest,
    db: Session = Depends(get_db),
):
    # Remove all existing slots.
    # The database foreign key cascade removes their bookings too.
    db.execute(delete(Slot))

    # Create the replacement slots.
    new_slots = [
        Slot(
            id=slot.id,
            provider=slot.provider,
            start_time=slot.start_time,
            end_time=slot.end_time,
        )
        for slot in request.slots
    ]

    db.add_all(new_slots)
    db.commit()

    return {"message": "Done"}


@router.get("/slots", response_model=SlotsResponse)
def get_slots(
    provider: str | None = None,
    db: Session = Depends(get_db),
):
    # A slot is unavailable if it has a confirmed booking.
    has_confirmed_booking = (
        select(Booking.id)
        .where(
            Booking.slot_id == Slot.id,
            Booking.status == "confirmed",
        )
        .exists()
    )

    # Select each slot alongside its calculated availability.
    statement = select(
        Slot,
        (~has_confirmed_booking).label("available"),
    )

    # Apply an exact provider-name filter if supplied.
    if provider is not None:
        statement = statement.where(Slot.provider == provider)

    statement = statement.order_by(Slot.start_time)
    results = db.execute(statement).all()

    slots = [
        {
            "id": slot.id,
            "provider": slot.provider,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "available": available,
        }
        for slot, available in results
    ]

    return {"slots": slots}


@router.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=201,
)
def create_booking(
    request: BookingCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
):
    # Validate the optional idempotency key.
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()

        if not idempotency_key or len(idempotency_key) > 255:
            raise HTTPException(
                status_code=400,
                detail="invalid idempotency key",
            )

    # Build a consistent representation of the request.
    normalized_email = str(request.email).strip().lower()
    request_data = {
        "slot_id": request.slot_id,
        "name": request.name,
        "email": normalized_email,
    }

    # Count this booking attempt before processing it.
    enforce_booking_rate_limit(
        db,
        request_data["email"],
    )

    # Generate a SHA-256 fingerprint of the request.
    request_hash = hashlib.sha256(
        json.dumps(
            request_data,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    # Helper to find a previous request using the same key.
    def find_existing_booking():
        if idempotency_key is None:
            return None

        return db.execute(
            select(Booking).where(Booking.idempotency_key == idempotency_key)
        ).scalar_one_or_none()

    # Check whether this request has already been processed.
    if idempotency_key is not None:
        existing = find_existing_booking()

        if existing is not None:
            if existing.request_hash != request_hash:
                raise HTTPException(
                    status_code=422,
                    detail="idempotency key reused with different request",
                )

            return existing

    # Lock the slot before checking its availability.
    slot = db.execute(
        select(Slot).where(Slot.id == request.slot_id).with_for_update()
    ).scalar_one_or_none()

    if slot is None:
        raise HTTPException(
            status_code=404,
            detail="slot not found",
        )

    # Check again after acquiring the slot lock.
    # Another identical request may have completed while this
    # request was waiting for the lock.
    if idempotency_key is not None:
        existing = find_existing_booking()

        if existing is not None:
            if existing.request_hash != request_hash:
                raise HTTPException(
                    status_code=422,
                    detail="idempotency key reused with different request",
                )

            return existing

    # Reject slots that have already started.
    now = datetime.now(UTC)

    if slot.start_time <= now:
        raise HTTPException(
            status_code=400,
            detail="slot has already started",
        )

    # Check whether the slot already has a confirmed booking.
    existing_booking = db.execute(
        select(Booking).where(
            Booking.slot_id == slot.id,
            Booking.status == "confirmed",
        )
    ).scalar_one_or_none()

    if existing_booking is not None:
        raise HTTPException(
            status_code=409,
            detail="slot already booked",
        )

    # Create the booking.
    booking = Booking(
        slot_id=slot.id,
        name=request.name,
        email=str(request.email),
        idempotency_key=idempotency_key,
        request_hash=request_hash if idempotency_key else None,
    )

    db.add(booking)

    try:
        db.commit()
        db.refresh(booking)

    except IntegrityError:
        db.rollback()

        # Another request may have inserted this idempotency key
        # while this request was processing.
        if idempotency_key is not None:
            existing = find_existing_booking()

            if existing is not None:
                if existing.request_hash != request_hash:
                    raise HTTPException(
                        status_code=422,
                        detail="idempotency key reused with different request",
                    )

                return existing

        raise HTTPException(
            status_code=409,
            detail="slot already booked",
        )

    return booking


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)

    if booking is None:
        raise HTTPException(
            status_code=404,
            detail="booking not found",
        )

    return booking


@router.delete(
    "/bookings/{booking_id}",
    response_model=BookingResponse,
)
def cancel_booking(
    booking_id: str,
    db: Session = Depends(get_db),
):
    # Find and lock the booking so simultaneous cancellation
    # requests cannot both modify it.
    booking = db.execute(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    ).scalar_one_or_none()

    if booking is None:
        raise HTTPException(
            status_code=404,
            detail="booking not found",
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=409,
            detail="booking already cancelled",
        )

    # Change the booking's state rather than deleting it.
    booking.status = "cancelled"

    db.commit()
    db.refresh(booking)

    return booking


@router.get(
    "/bookings",
    response_model=BookingPageResponse,
)
def list_bookings(
    email: EmailStr = Query(...),
    limit: int = Query(default=10, ge=1, le=50),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # Normalize the email address.
    normalized_email = str(email).strip().lower()

    # Start with bookings belonging to this email.
    statement = select(Booking).where(func.lower(Booking.email) == normalized_email)

    # If a cursor was supplied, retrieve its position.
    if cursor is not None:
        cursor_created_at, cursor_id = decode_cursor(cursor)

        # Retrieve records strictly after the previous page.
        statement = statement.where(
            or_(
                Booking.created_at > cursor_created_at,
                ((Booking.created_at == cursor_created_at) & (Booking.id > cursor_id)),
            )
        )

    # Consistent ordering prevents records from moving
    # unpredictably between pages.
    statement = statement.order_by(
        Booking.created_at.asc(),
        Booking.id.asc(),
    )

    # Fetch one additional record to determine whether
    # another page exists.
    results = db.scalars(statement.limit(limit + 1)).all()

    has_more = len(results) > limit

    # Return only the requested number of bookings.
    bookings = results[:limit]

    # Create a cursor from the last returned booking.
    next_cursor = None

    if has_more:
        next_cursor = encode_cursor(bookings[-1])

    return {
        "bookings": bookings,
        "next_cursor": next_cursor,
    }

import math
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.models import BookingAttempt

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60


def enforce_booking_rate_limit(
    db: Session,
    email: str,
) -> None:
    normalized_email = email.strip().lower()

    # Serialize rate-limit checks for the same email.
    # This prevents simultaneous requests from bypassing the limit.
    db.execute(
        text(
            """
            SELECT pg_advisory_xact_lock(
                hashtextextended(:email, 0)
            )
            """
        ),
        {"email": normalized_email},
    )

    # Use PostgreSQL's clock for consistent timing.
    now = db.scalar(select(func.now()))
    window_start = now - timedelta(seconds=WINDOW_SECONDS)

    # Remove expired attempts for this email.
    db.execute(
        delete(BookingAttempt).where(
            BookingAttempt.email == normalized_email,
            BookingAttempt.attempted_at < window_start,
        )
    )

    # Count attempts within the last 60 seconds.
    attempts = db.scalar(
        select(func.count())
        .select_from(BookingAttempt)
        .where(
            BookingAttempt.email == normalized_email,
            BookingAttempt.attempted_at >= window_start,
        )
    )

    if attempts >= MAX_ATTEMPTS:
        oldest_attempt = db.scalar(
            select(func.min(BookingAttempt.attempted_at)).where(
                BookingAttempt.email == normalized_email,
                BookingAttempt.attempted_at >= window_start,
            )
        )

        retry_after = math.ceil(
            (oldest_attempt + timedelta(seconds=WINDOW_SECONDS) - now).total_seconds()
        )

        # Release the database lock.
        db.rollback()

        raise HTTPException(
            status_code=429,
            detail="too many booking attempts",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    # Record the attempt and commit immediately.
    # This ensures failed booking operations still count.
    db.add(
        BookingAttempt(
            email=normalized_email,
            attempted_at=now,
        )
    )

    db.commit()

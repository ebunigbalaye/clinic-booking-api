from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        CheckConstraint(
            "end_time > start_time",
            name="ck_slots_end_after_start",
        ),
        Index(
            "ix_slots_start",
            "start_time",
        ),
        Index(
            "ix_slots_provider_start",
            "provider",
            "start_time",
        ),
    )
    id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )
    provider: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="slot",
        passive_deletes=True,
    )


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('confirmed', 'cancelled')",
            name="ck_bookings_valid_status",
        ),
        Index(
            "uq_bookings_one_confirmed_per_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("status = 'confirmed'"),
        ),
        Index(
            "ix_bookings_email_created_at_id",
            "email",
            "created_at",
            "id",
        ),
        Index(
            "uq_bookings_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    slot_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="confirmed",
        server_default=text("'confirmed'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    slot: Mapped["Slot"] = relationship(
        back_populates="bookings",
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    request_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )


class BookingAttempt(Base):
    __tablename__ = "booking_attempts"
    __table_args__ = (
        Index(
            "ix_booking_attempts_email_attempted_at",
            "email",
            "attempted_at",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

from app.config import settings
from app.models import Booking, Slot


def test_two_users_cannot_book_same_slot_concurrently(
    db_session, concurrent_client_factory
):
    # Create one appointment slot in the test database.
    start = datetime.now(UTC) + timedelta(days=1)

    db_session.add(
        Slot(
            id="concurrent-slot",
            provider="Dr Ade",
            start_time=start,
            end_time=start + timedelta(minutes=30),
        )
    )
    db_session.commit()

    # Both requests must reach the booking operation together.
    barrier = Barrier(2)

    def attempt_booking(name, email):
        with concurrent_client_factory() as client:
            barrier.wait()

            return client.post(
                "/bookings",
                json={
                    "slot_id": "concurrent-slot",
                    "name": name,
                    "email": email,
                },
                headers={"X-API-Key": settings.API_KEY},
            )

    # Execute both requests in separate threads.
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(attempt_booking, "Ada Obi", "ada@example.com")
        second = executor.submit(attempt_booking, "John Doe", "john@example.com")

        responses = [first.result(), second.result()]

    # Exactly one request must succeed.
    statuses = sorted(response.status_code for response in responses)

    assert statuses == [201, 409]

    # Verify that only one confirmed booking exists in the database.
    confirmed_bookings = (
        db_session.query(Booking)
        .filter(
            Booking.slot_id == "concurrent-slot",
            Booking.status == "confirmed",
        )
        .count()
    )

    assert confirmed_bookings == 1

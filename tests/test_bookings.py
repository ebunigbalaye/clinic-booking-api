def test_create_booking(client, auth_headers, populated_slots):
    response = client.post(
        "/bookings",
        json={
            "slot_id": "s1",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201

    booking = response.json()
    assert booking["slot_id"] == "s1"
    assert booking["name"] == "Ada Obi"
    assert booking["email"] == "ada@example.com"
    assert booking["status"] == "confirmed"
    assert "id" in booking
    assert "created_at" in booking


def test_get_booking_by_id(client, auth_headers, populated_slots):
    create_response = client.post(
        "/bookings",
        json={
            "slot_id": "s1",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=auth_headers,
    )

    booking_id = create_response.json()["id"]

    response = client.get(
        f"/bookings/{booking_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == booking_id
    assert response.json()["email"] == "ada@example.com"


def test_get_nonexistent_booking_returns_404(client, auth_headers):
    response = client.get(
        "/bookings/nonexistent-id",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_cannot_book_an_already_booked_slot(client, auth_headers, populated_slots):
    booking_data = {
        "slot_id": "s1",
        "name": "Ada Obi",
        "email": "ada@example.com",
    }

    first_response = client.post("/bookings", json=booking_data, headers=auth_headers)
    second_response = client.post(
        "/bookings",
        json={
            "slot_id": "s1",
            "name": "John Doe",
            "email": "john@example.com",
        },
        headers=auth_headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_booking_makes_slot_unavailable(client, auth_headers, populated_slots):
    client.post(
        "/bookings",
        json={
            "slot_id": "s1",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=auth_headers,
    )

    response = client.get("/slots", headers=auth_headers)

    slots = response.json()["slots"]
    booked_slot = next(slot for slot in slots if slot["id"] == "s1")

    assert booked_slot["available"] is False


def test_cancel_booking(client, auth_headers, populated_slots):
    create_response = client.post(
        "/bookings",
        json={
            "slot_id": "s1",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=auth_headers,
    )

    booking_id = create_response.json()["id"]

    response = client.delete(
        f"/bookings/{booking_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancelling_booking_makes_slot_available_again(
    client, auth_headers, populated_slots
):
    create_response = client.post(
        "/bookings",
        json={
            "slot_id": "s1",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=auth_headers,
    )

    booking_id = create_response.json()["id"]

    client.delete(
        f"/bookings/{booking_id}",
        headers=auth_headers,
    )

    response = client.get("/slots", headers=auth_headers)
    slots = response.json()["slots"]
    slot = next(item for item in slots if item["id"] == "s1")

    assert slot["available"] is True


def test_cannot_cancel_booking_twice(client, auth_headers, populated_slots):
    create_response = client.post(
        "/bookings",
        json={
            "slot_id": "s1",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=auth_headers,
    )

    booking_id = create_response.json()["id"]

    first_cancel = client.delete(
        f"/bookings/{booking_id}",
        headers=auth_headers,
    )
    second_cancel = client.delete(
        f"/bookings/{booking_id}",
        headers=auth_headers,
    )

    assert first_cancel.status_code == 200
    assert second_cancel.status_code == 409


def test_cannot_book_nonexistent_slot(client, auth_headers):
    response = client.post(
        "/bookings",
        json={
            "slot_id": "does-not-exist",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404

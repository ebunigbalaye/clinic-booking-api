def test_same_key_and_same_body_returns_same_booking(
    client, auth_headers, populated_slots
):
    payload = {
        "slot_id": "s1",
        "name": "Ada Obi",
        "email": "ada@example.com",
    }
    headers = {
        **auth_headers,
        "Idempotency-Key": "booking-request-001",
    }

    first = client.post("/bookings", json=payload, headers=headers)
    second = client.post("/bookings", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_same_key_with_different_body_returns_422(
    client, auth_headers, populated_slots
):
    headers = {
        **auth_headers,
        "Idempotency-Key": "booking-request-002",
    }

    first = client.post(
        "/bookings",
        json={
            "slot_id": "s1",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=headers,
    )

    second = client.post(
        "/bookings",
        json={
            "slot_id": "s2",
            "name": "John Doe",
            "email": "john@example.com",
        },
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 422


def test_requests_without_idempotency_keys_are_independent(
    client, auth_headers, populated_slots
):
    first = client.post(
        "/bookings",
        json={
            "slot_id": "s1",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=auth_headers,
    )

    second = client.post(
        "/bookings",
        json={
            "slot_id": "s2",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        headers=auth_headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]

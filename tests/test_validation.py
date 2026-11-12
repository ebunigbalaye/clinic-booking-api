import pytest


@pytest.mark.parametrize(
    "payload",
    [
        {
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        {
            "slot_id": "s1",
            "email": "ada@example.com",
        },
        {
            "slot_id": "s1",
            "name": "Ada Obi",
        },
    ],
)
def test_missing_booking_fields_are_rejected(
    client, auth_headers, populated_slots, payload
):
    response = client.post(
        "/bookings",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.parametrize(
    "payload",
    [
        {
            "slot_id": "",
            "name": "Ada Obi",
            "email": "ada@example.com",
        },
        {
            "slot_id": "s1",
            "name": "",
            "email": "ada@example.com",
        },
        {
            "slot_id": "s1",
            "name": "Ada Obi",
            "email": "not-an-email",
        },
    ],
)
def test_invalid_booking_fields_are_rejected(
    client, auth_headers, populated_slots, payload
):
    response = client.post(
        "/bookings",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "error" in response.json()


def test_booking_input_is_normalized(client, auth_headers, populated_slots):
    response = client.post(
        "/bookings",
        json={
            "slot_id": " s1 ",
            "name": "  Ada Obi  ",
            "email": " ADA@EXAMPLE.COM ",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201

    booking = response.json()
    assert booking["slot_id"] == "s1"
    assert booking["name"] == "Ada Obi"
    assert booking["email"] == "ada@example.com"

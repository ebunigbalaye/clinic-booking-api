def create_booking(client, auth_headers, slot_id, email="ada@example.com"):
    return client.post(
        "/bookings",
        json={
            "slot_id": slot_id,
            "name": "Ada Obi",
            "email": email,
        },
        headers=auth_headers,
    )


def test_first_page_returns_requested_limit(client, auth_headers, populated_slots):
    for slot_id in ["s1", "s2", "s3"]:
        response = create_booking(client, auth_headers, slot_id)
        assert response.status_code == 201

    response = client.get(
        "/bookings?email=ada@example.com&limit=2",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.json()["bookings"]) == 2
    assert response.json()["next_cursor"] is not None


def test_next_page_returns_remaining_bookings(client, auth_headers, populated_slots):
    for slot_id in ["s1", "s2", "s3"]:
        create_booking(client, auth_headers, slot_id)

    first_page = client.get(
        "/bookings?email=ada@example.com&limit=2",
        headers=auth_headers,
    ).json()

    second_page = client.get(
        "/bookings",
        params={
            "email": "ada@example.com",
            "limit": 2,
            "cursor": first_page["next_cursor"],
        },
        headers=auth_headers,
    )

    assert second_page.status_code == 200
    assert len(second_page.json()["bookings"]) == 1
    assert second_page.json()["next_cursor"] is None


def test_pagination_has_no_duplicate_bookings(client, auth_headers, populated_slots):
    for slot_id in ["s1", "s2", "s3"]:
        create_booking(client, auth_headers, slot_id)

    first_page = client.get(
        "/bookings?email=ada@example.com&limit=2",
        headers=auth_headers,
    ).json()

    second_page = client.get(
        "/bookings",
        params={
            "email": "ada@example.com",
            "limit": 2,
            "cursor": first_page["next_cursor"],
        },
        headers=auth_headers,
    ).json()

    first_ids = [b["id"] for b in first_page["bookings"]]
    second_ids = [b["id"] for b in second_page["bookings"]]

    assert len(set(first_ids + second_ids)) == 3


def test_pagination_filters_by_email(client, auth_headers, populated_slots):
    create_booking(client, auth_headers, "s1", "ada@example.com")
    create_booking(client, auth_headers, "s2", "john@example.com")

    response = client.get(
        "/bookings?email=ADA@EXAMPLE.COM",
        headers=auth_headers,
    )

    assert response.status_code == 200

    bookings = response.json()["bookings"]
    assert len(bookings) == 1
    assert bookings[0]["email"] == "ada@example.com"


def test_pagination_rejects_invalid_limit(client, auth_headers):
    response = client.get(
        "/bookings?email=ada@example.com&limit=100",
        headers=auth_headers,
    )

    assert response.status_code == 400

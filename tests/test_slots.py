def test_reset_slots(client, auth_headers, sample_slots):
    response = client.post(
        "/reset",
        json={"slots": sample_slots},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Done"}


def test_reset_replaces_existing_slots(
    client,
    auth_headers,
    sample_slots,
):
    client.post(
        "/reset",
        json={"slots": sample_slots},
        headers=auth_headers,
    )

    replacement_slots = [
        {
            "id": "s4",
            "provider": "Dr Musa",
            "start_time": "2099-12-11T09:00:00Z",
            "end_time": "2099-12-11T09:30:00Z",
        }
    ]

    client.post(
        "/reset",
        json={"slots": replacement_slots},
        headers=auth_headers,
    )

    response = client.get(
        "/slots",
        headers=auth_headers,
    )

    slots = response.json()["slots"]

    assert len(slots) == 1
    assert slots[0]["id"] == "s4"


def test_get_slots_returns_all_slots(
    client,
    auth_headers,
    populated_slots,
):
    response = client.get(
        "/slots",
        headers=auth_headers,
    )

    assert response.status_code == 200

    slots = response.json()["slots"]

    assert len(slots) == 3
    assert slots[0]["id"] == "s1"
    assert slots[1]["id"] == "s2"
    assert slots[2]["id"] == "s3"


def test_get_slots_filters_by_provider(
    client,
    auth_headers,
    populated_slots,
):
    response = client.get(
        "/slots?provider=Dr%20Ade",
        headers=auth_headers,
    )

    assert response.status_code == 200

    slots = response.json()["slots"]

    assert len(slots) == 2
    assert all(slot["provider"] == "Dr Ade" for slot in slots)


def test_new_slots_are_available(
    client,
    auth_headers,
    populated_slots,
):
    response = client.get(
        "/slots",
        headers=auth_headers,
    )

    slots = response.json()["slots"]

    assert all(slot["available"] is True for slot in slots)

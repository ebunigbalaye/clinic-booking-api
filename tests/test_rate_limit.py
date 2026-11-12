def make_booking_attempt(client, auth_headers, email):
    return client.post(
        "/bookings",
        json={
            "slot_id": "nonexistent-slot",
            "name": "Test User",
            "email": email,
        },
        headers=auth_headers,
    )


def test_first_five_attempts_are_allowed(client, auth_headers):
    for _ in range(5):
        response = make_booking_attempt(client, auth_headers, "ada@example.com")

        # The slot does not exist, but the attempt is allowed.
        assert response.status_code == 404


def test_sixth_attempt_is_rate_limited(client, auth_headers):
    for _ in range(5):
        make_booking_attempt(client, auth_headers, "ada@example.com")

    response = make_booking_attempt(client, auth_headers, "ada@example.com")

    assert response.status_code == 429
    assert "error" in response.json()


def test_rate_limit_includes_retry_after_header(client, auth_headers):
    for _ in range(5):
        make_booking_attempt(client, auth_headers, "ada@example.com")

    response = make_booking_attempt(client, auth_headers, "ada@example.com")

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) >= 1


def test_different_emails_have_separate_rate_limits(client, auth_headers):
    for _ in range(5):
        make_booking_attempt(client, auth_headers, "ada@example.com")

    blocked = make_booking_attempt(client, auth_headers, "ada@example.com")

    other_email = make_booking_attempt(client, auth_headers, "john@example.com")

    assert blocked.status_code == 429
    assert other_email.status_code == 404


def test_failed_attempts_count_towards_rate_limit(client, auth_headers):
    for _ in range(5):
        response = make_booking_attempt(client, auth_headers, "ada@example.com")
        assert response.status_code == 404

    response = make_booking_attempt(client, auth_headers, "ada@example.com")

    assert response.status_code == 429

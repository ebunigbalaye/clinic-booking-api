def test_request_without_api_key_is_rejected(client):
    response = client.get("/slots")

    assert response.status_code == 401
    assert "error" in response.json()


def test_request_with_invalid_api_key_is_rejected(client):
    response = client.get(
        "/slots",
        headers={"X-API-Key": "wrong-api-key"},
    )

    assert response.status_code == 401


def test_request_with_valid_api_key_is_allowed(client, auth_headers):
    response = client.get("/slots", headers=auth_headers)

    assert response.status_code == 200

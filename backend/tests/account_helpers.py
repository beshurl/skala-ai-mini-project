"""Disposable UNIT_TEST_FIXTURE accounts; never use these credentials outside tests."""
import uuid

PASSWORD = "UNIT_TEST_FIXTURE-password-2026"


def signup(client, email=None):
    response = client.post("/api/auth/register", json={"email": email or uuid.uuid4().hex + "@example.test",
                           "password": PASSWORD, "name": "UNIT_TEST_FIXTURE"})
    assert response.status_code == 201, response.text
    return response.json()


def enter_demo(client):
    current = client.get("/api/auth/session")
    profile = current.json() if current.status_code == 200 else signup(client)
    return client.post("/api/demo", headers={"x-recase-csrf": profile["csrf"]})

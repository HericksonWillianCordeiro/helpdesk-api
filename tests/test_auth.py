def test_register_login_and_me(client) -> None:
    register = client.post(
        "/auth/register",
        json={"name": "Ana", "email": "ANA@example.com", "password": "secret123"},
    )
    assert register.status_code == 201
    assert register.json()["email"] == "ana@example.com"

    login = client.post(
        "/auth/login",
        data={"username": "ana@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["name"] == "Ana"


def test_invalid_login_and_token_are_rejected(client) -> None:
    client.post(
        "/auth/register",
        json={"name": "Ana", "email": "ana@example.com", "password": "secret123"},
    )
    invalid_login = client.post(
        "/auth/login",
        data={"username": "ana@example.com", "password": "wrongpass"},
    )
    assert invalid_login.status_code == 401
    invalid_token = client.get(
        "/auth/me", headers={"Authorization": "Bearer invalid-token"}
    )
    assert invalid_token.status_code == 401


def test_malformed_numeric_subject_is_rejected(client) -> None:
    from app.core.security import create_access_token

    token = create_access_token("not-a-user-id")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_user_can_correct_own_name(client) -> None:
    client.post(
        "/auth/register",
        json={
            "name": "Nome errado",
            "email": "correcao@example.com",
            "password": "secret123",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": "correcao@example.com", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.patch("/auth/me", json={"name": "Nome correto"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Nome correto"


def test_refresh_token_rotates_and_logout_revokes_it(client) -> None:
    client.post(
        "/auth/register",
        json={
            "name": "Refresh User",
            "email": "refresh@example.com",
            "password": "secret123",
        },
    )
    login = client.post(
        "/auth/login", data={"username": "refresh@example.com", "password": "secret123"}
    )
    tokens = login.json()

    refreshed = client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

    headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    logout = client.post(
        "/auth/logout",
        json={"refresh_token": refreshed.json()["refresh_token"]},
        headers=headers,
    )
    assert logout.status_code == 204
    revoked = client.post(
        "/auth/refresh", json={"refresh_token": refreshed.json()["refresh_token"]}
    )
    assert revoked.status_code == 401

from app.core.security import hash_password
from app.models import Category, User
from app.models.enums import UserRole


def seed_user(db, email: str, role: UserRole) -> User:
    user = User(
        name=role.value.title(),
        email=email,
        password_hash=hash_password("secret123"),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def token_for(client, email: str) -> str:
    response = client.post(
        "/auth/login", data={"username": email, "password": "secret123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_ticket_permissions_assignment_comments_and_dashboard(client) -> None:
    from sqlalchemy.orm import Session

    from tests.conftest import engine

    with Session(engine) as db:
        admin = seed_user(db, "admin@example.com", UserRole.ADMIN)
        technician = seed_user(db, "tech@example.com", UserRole.TECHNICIAN)
        admin_email = admin.email
        technician_email = technician.email
        technician_id = technician.id
    admin_headers = {"Authorization": f"Bearer {token_for(client, admin_email)}"}
    tech_headers = {"Authorization": f"Bearer {token_for(client, technician_email)}"}

    denied_category = client.post(
        "/categories", json={"name": "Hardware"}, headers=tech_headers
    )
    assert denied_category.status_code == 403
    denied_ticket = client.post(
        "/tickets",
        json={
            "title": "Admin ticket",
            "description": "Não permitido",
            "category_id": 1,
        },
        headers=admin_headers,
    )
    assert denied_ticket.status_code == 403
    category = client.post(
        "/categories", json={"name": "Hardware"}, headers=admin_headers
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    user = client.post(
        "/auth/register",
        json={
            "name": "Requester",
            "email": "requester@example.com",
            "password": "secret123",
        },
    )
    user_headers = {
        "Authorization": f"Bearer {token_for(client, 'requester@example.com')}"
    }
    ticket = client.post(
        "/tickets",
        json={
            "title": "Notebook",
            "description": "Não liga",
            "category_id": category_id,
        },
        headers=user_headers,
    )
    assert ticket.status_code == 201
    ticket_id = ticket.json()["id"]
    admin_notifications = client.get("/notifications", headers=admin_headers)
    assert admin_notifications.status_code == 200
    assert admin_notifications.json()[0]["title"] == "Novo chamado"
    denied_resolution = client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "RESOLVED", "resolution_note": "Admin não pode resolver"},
        headers=admin_headers,
    )
    assert denied_resolution.status_code == 403

    assert client.get("/tickets", headers=tech_headers).json()["items"] == []
    assigned = client.patch(
        f"/tickets/{ticket_id}/assign",
        json={"technician_id": technician_id},
        headers=admin_headers,
    )
    assert assigned.status_code == 200
    tech_notifications = client.get("/notifications", headers=tech_headers)
    assert tech_notifications.status_code == 200
    assert tech_notifications.json()[0]["title"] == "Chamado atribuído"
    assert (
        client.get("/tickets", headers=tech_headers).json()["items"][0]["id"]
        == ticket_id
    )
    unassigned = client.patch(
        f"/tickets/{ticket_id}/assign",
        json={"technician_id": None},
        headers=admin_headers,
    )
    assert unassigned.status_code == 200
    assert unassigned.json()["technician_id"] is None
    assert client.get("/tickets", headers=tech_headers).json()["items"] == []
    reassigned = client.patch(
        f"/tickets/{ticket_id}/assign",
        json={"technician_id": technician_id},
        headers=admin_headers,
    )
    assert reassigned.status_code == 200

    status_update = client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "RESOLVED", "resolution_note": "Troca de peça realizada"},
        headers=tech_headers,
    )
    assert status_update.status_code == 200
    assert status_update.json()["resolved_at"] is not None
    updated_admin_notifications = client.get("/notifications", headers=admin_headers)
    assert any(
        notification["title"] == "Chamado resolvido"
        for notification in updated_admin_notifications.json()
    )
    mark_all = client.patch("/notifications/read-all", headers=admin_headers)
    assert mark_all.status_code == 204
    assert all(
        notification["is_read"]
        for notification in client.get("/notifications", headers=admin_headers).json()
    )
    comments = client.get(f"/tickets/{ticket_id}/comments", headers=user_headers)
    assert comments.status_code == 200
    assert comments.json()[0]["content"] == "Nota de solução: Troca de peça realizada"
    comment = client.post(
        f"/tickets/{ticket_id}/comments",
        json={"content": "Problema resolvido"},
        headers=tech_headers,
    )
    assert comment.status_code == 201
    user_comment = client.post(
        f"/tickets/{ticket_id}/comments",
        json={"content": "Obrigado pelo retorno"},
        headers=user_headers,
    )
    assert user_comment.status_code == 201
    assert user_comment.json()["author_name"] == "Requester"
    closed = client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "CLOSED"},
        headers=tech_headers,
    )
    assert closed.status_code == 200
    closed_notifications = client.get("/notifications", headers=admin_headers)
    assert any(
        notification["title"] == "Chamado fechado"
        and "como CLOSED" in notification["message"]
        for notification in closed_notifications.json()
    )
    dashboard = client.get("/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total"] == 1
    assert dashboard.json()["resolved"] == 0
    assert dashboard.json()["closed"] == 1
    assert dashboard.json()["by_technician"][str(technician_id)] == 1


def test_admin_can_create_a_user_with_role(client) -> None:
    from sqlalchemy.orm import Session

    from tests.conftest import engine

    with Session(engine) as db:
        admin = seed_user(db, "admin-create@example.com", UserRole.ADMIN)
        admin_email = admin.email
    headers = {"Authorization": f"Bearer {token_for(client, admin_email)}"}

    response = client.post(
        "/users",
        json={
            "name": "Novo Técnico",
            "email": "novo-tech@example.com",
            "password": "secret123",
            "role": "TECHNICIAN",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["role"] == "TECHNICIAN"


def test_admin_can_delete_unused_user(client) -> None:
    from sqlalchemy.orm import Session

    from tests.conftest import engine

    with Session(engine) as db:
        admin = seed_user(db, "admin-delete@example.com", UserRole.ADMIN)
        admin_email = admin.email
    headers = {"Authorization": f"Bearer {token_for(client, admin_email)}"}
    created = client.post(
        "/users",
        json={
            "name": "Conta temporária",
            "email": "temp@example.com",
            "password": "secret123",
        },
        headers=headers,
    )

    deleted = client.delete(f"/users/{created.json()['id']}", headers=headers)

    assert deleted.status_code == 204

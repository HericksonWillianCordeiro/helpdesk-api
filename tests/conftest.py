import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-chars"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.core.database import Base
from app.main import app
from app.models import AuditLog, Category, Notification, Ticket, TicketComment, User

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)


def override_get_db():
    with Session(engine) as db:
        yield db


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client() -> TestClient:
    with Session(engine) as db:
        db.query(TicketComment).delete()
        db.query(AuditLog).delete()
        db.query(Notification).delete()
        db.query(Ticket).delete()
        db.query(Category).delete()
        db.query(User).delete()
        db.commit()
    return TestClient(app)

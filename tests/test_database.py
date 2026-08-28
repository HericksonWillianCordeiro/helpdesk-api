from sqlalchemy import inspect

from app.core.database import Base
from app.models import AuditLog, Category, Ticket, TicketComment, User


def test_all_phase_two_models_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "categories",
        "tickets",
        "ticket_comments",
        "audit_logs",
        "notifications",
        "sla_policies",
        "refresh_tokens",
    }


def test_relationship_foreign_keys_are_defined() -> None:
    assert {
        foreign_key.target_fullname for foreign_key in Ticket.__table__.foreign_keys
    } == {
        "users.id",
        "categories.id",
    }
    assert {
        foreign_key.target_fullname
        for foreign_key in TicketComment.__table__.foreign_keys
    } == {
        "tickets.id",
        "users.id",
    }
    assert {
        foreign_key.target_fullname for foreign_key in AuditLog.__table__.foreign_keys
    } == {
        "users.id",
    }
    assert set(inspect(User).relationships.keys()) >= {
        "created_tickets",
        "assigned_tickets",
        "comments",
        "audit_logs",
    }
    assert set(inspect(Category).relationships.keys()) == {"tickets"}

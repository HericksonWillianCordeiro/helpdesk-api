from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import Category, Ticket, User
from app.models.enums import TicketPriority, TicketStatus, UserRole

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def scoped_tickets(current_user: User):
    query = select(Ticket)
    if current_user.role == UserRole.USER:
        query = query.where(Ticket.user_id == current_user.id)
    elif current_user.role == UserRole.TECHNICIAN:
        query = query.where(Ticket.technician_id == current_user.id)
    return query.subquery()


@router.get("")
def dashboard(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, object]:
    tickets = scoped_tickets(current_user)
    total = db.scalar(select(func.count()).select_from(tickets)) or 0
    overdue = (
        db.scalar(
            select(func.count())
            .select_from(tickets)
            .where(
                tickets.c.sla_due_at < func.now(),
                tickets.c.status.not_in((TicketStatus.RESOLVED, TicketStatus.CLOSED)),
            )
        )
        or 0
    )
    status_rows = db.execute(
        select(tickets.c.status, func.count()).group_by(tickets.c.status)
    ).all()
    priority_rows = db.execute(
        select(tickets.c.priority, func.count()).group_by(tickets.c.priority)
    ).all()
    category_rows = db.execute(
        select(Category.name, func.count(tickets.c.id))
        .join(tickets, tickets.c.category_id == Category.id)
        .group_by(Category.name)
    ).all()
    technician_rows = db.execute(
        select(tickets.c.technician_id, func.count())
        .where(tickets.c.technician_id.is_not(None))
        .group_by(tickets.c.technician_id)
    ).all()
    return {
        "total": total,
        "overdue": overdue,
        "open": _value(status_rows, TicketStatus.OPEN),
        "in_progress": _value(status_rows, TicketStatus.IN_PROGRESS),
        "resolved": _value(status_rows, TicketStatus.RESOLVED),
        "closed": _value(status_rows, TicketStatus.CLOSED),
        "critical": _value(priority_rows, TicketPriority.CRITICAL),
        "by_priority": {str(row[0]): row[1] for row in priority_rows},
        "by_category": {row[0]: row[1] for row in category_rows},
        "by_technician": {str(row[0]): row[1] for row in technician_rows},
    }


def _value(rows, expected) -> int:
    return next((row[1] for row in rows if row[0] == expected), 0)

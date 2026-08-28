from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SlaPolicy
from app.models.enums import TicketPriority

SLA_HOURS = {
    TicketPriority.CRITICAL: 4,
    TicketPriority.HIGH: 8,
    TicketPriority.MEDIUM: 24,
    TicketPriority.LOW: 72,
}


def deadline_for(
    priority: TicketPriority, created_at: datetime, db: Session
) -> datetime:
    hours = db.scalar(
        select(SlaPolicy.resolution_hours).where(SlaPolicy.priority == priority)
    )
    return created_at + timedelta(hours=hours or SLA_HOURS[priority])

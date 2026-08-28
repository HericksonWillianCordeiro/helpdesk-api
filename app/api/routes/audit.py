from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.api.routes.tickets import get_visible_ticket
from app.core.database import get_db
from app.models import AuditLog, User
from app.schemas.audit import AuditRead

router = APIRouter(prefix="/tickets/{ticket_id}/audit", tags=["Audit"])


@router.get("", response_model=list[AuditRead])
def list_ticket_audit(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditLog]:
    ticket = get_visible_ticket(ticket_id, current_user, db)
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.entity == "Ticket", AuditLog.entity_id == ticket.id)
            .options(selectinload(AuditLog.user))
            .order_by(AuditLog.created_at)
        )
    )

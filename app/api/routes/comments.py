from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.api.routes.tickets import get_visible_ticket
from app.core.database import get_db
from app.models import TicketComment, User
from app.schemas.ticket import CommentCreate, CommentRead
from app.services.audit import record_audit

router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["Comments"])


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(
    ticket_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketComment:
    ticket = get_visible_ticket(ticket_id, current_user, db)
    if ticket.status.value == "CLOSED":
        raise HTTPException(
            status_code=409, detail="Chamado fechado não aceita comentários"
        )
    comment = TicketComment(
        ticket_id=ticket.id,
        user_id=current_user.id,
        content=payload.content,
        user=current_user,
    )
    db.add(comment)
    db.flush()
    record_audit(db, current_user.id, "COMMENT", "Ticket", ticket.id)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("", response_model=list[CommentRead])
def list_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TicketComment]:
    ticket = get_visible_ticket(ticket_id, current_user, db)
    return list(
        db.scalars(
            select(TicketComment)
            .where(TicketComment.ticket_id == ticket.id)
            .options(selectinload(TicketComment.user))
            .order_by(TicketComment.created_at)
        )
    )

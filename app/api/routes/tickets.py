from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
    require_admin,
    require_requester,
    require_technician,
)
from app.core.database import get_db
from app.models import Category, Ticket, TicketComment, User
from app.models.enums import TicketPriority, TicketStatus, UserRole
from app.schemas.ticket import (
    TicketAssign,
    TicketCreate,
    TicketPage,
    TicketRead,
    TicketStatusUpdate,
    TicketUpdate,
)
from app.services.audit import record_audit
from app.services.notification import notify_admins, notify_user
from app.services.sla import deadline_for

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def visible_query(user: User) -> Select[tuple[Ticket]]:
    query = select(Ticket).order_by(Ticket.created_at.desc())
    if user.role == UserRole.USER:
        return query.where(Ticket.user_id == user.id)
    if user.role == UserRole.TECHNICIAN:
        return query.where(Ticket.technician_id == user.id)
    return query


def get_visible_ticket(ticket_id: int, user: User, db: Session) -> Ticket:
    ticket = db.scalar(visible_query(user).where(Ticket.id == ticket_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    return ticket


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_requester),
) -> Ticket:
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    ticket = Ticket(**payload.model_dump(), user_id=current_user.id)
    ticket.sla_due_at = deadline_for(ticket.priority, datetime.now(), db)
    db.add(ticket)
    db.flush()
    record_audit(db, current_user.id, "CREATE", "Ticket", ticket.id)
    notify_admins(
        db,
        "Novo chamado",
        f"{current_user.name} abriu o chamado #{ticket.id}: {ticket.title}",
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("", response_model=TicketPage)
def list_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    category: int | None = Query(default=None, gt=0),
    technician: int | None = Query(default=None, gt=0),
    user: int | None = Query(default=None, gt=0),
    date_from: date | None = Query(default=None, alias="data_inicial"),
    date_to: date | None = Query(default=None, alias="data_final"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TicketPage:
    query = visible_query(current_user)
    if status_filter:
        query = query.where(Ticket.status == status_filter)
    if priority:
        query = query.where(Ticket.priority == priority)
    if category:
        query = query.where(Ticket.category_id == category)
    if technician:
        query = query.where(Ticket.technician_id == technician)
    if user and current_user.role == UserRole.ADMIN:
        query = query.where(Ticket.user_id == user)
    if date_from:
        query = query.where(Ticket.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.where(Ticket.created_at <= datetime.combine(date_to, time.max))
    total = (
        db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        or 0
    )
    items = list(db.scalars(query.offset((page - 1) * limit).limit(limit)))
    pages = (total + limit - 1) // limit
    return TicketPage(items=items, page=page, limit=limit, total=total, pages=pages)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    return get_visible_ticket(ticket_id, current_user, db)


@router.put("/{ticket_id}", response_model=TicketRead)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    ticket = get_visible_ticket(ticket_id, current_user, db)
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=409, detail="Chamado fechado não pode ser alterado"
        )
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes and db.get(Category, changes["category_id"]) is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    for field, value in changes.items():
        setattr(ticket, field, value)
    if "priority" in changes:
        ticket.sla_due_at = deadline_for(ticket.priority, ticket.created_at, db)
    record_audit(db, current_user.id, "UPDATE", "Ticket", ticket.id, changes)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/{ticket_id}/status", response_model=TicketRead)
def update_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_technician),
) -> Ticket:
    ticket = get_visible_ticket(ticket_id, current_user, db)
    if current_user.role == UserRole.ADMIN and payload.status == TicketStatus.RESOLVED:
        raise HTTPException(
            status_code=403,
            detail="Apenas o técnico pode marcar o chamado como resolvido",
        )
    if payload.status == TicketStatus.RESOLVED and not payload.resolution_note:
        raise HTTPException(
            status_code=422,
            detail="Descreva o que foi feito antes de marcar o chamado como resolvido",
        )
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=409, detail="Chamado fechado não pode ser alterado"
        )
    ticket.status = payload.status
    ticket.resolved_at = (
        datetime.now() if payload.status == TicketStatus.RESOLVED else None
    )
    if payload.resolution_note:
        db.add(
            TicketComment(
                ticket_id=ticket.id,
                user_id=current_user.id,
                content=f"Nota de solução: {payload.resolution_note}",
                user=current_user,
            )
        )
    record_audit(db, current_user.id, "STATUS_CHANGE", "Ticket", ticket.id)
    notification_title = {
        TicketStatus.RESOLVED: "Chamado resolvido",
        TicketStatus.CLOSED: "Chamado fechado",
    }.get(payload.status, "Status atualizado")
    notify_admins(
        db,
        notification_title,
        (
            f"{current_user.name} marcou o chamado #{ticket.id} "
            f"como {payload.status.value}"
        ),
    )
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/{ticket_id}/assign", response_model=TicketRead)
def assign_ticket(
    ticket_id: int,
    payload: TicketAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    if payload.technician_id is None:
        ticket.technician_id = None
        action = "UNASSIGN"
    else:
        technician = db.get(User, payload.technician_id)
        if technician is None or technician.role != UserRole.TECHNICIAN:
            raise HTTPException(status_code=404, detail="Técnico não encontrado")
        ticket.technician_id = technician.id
        action = "ASSIGN"
        notify_user(
            db,
            technician.id,
            "Chamado atribuído",
            f"O chamado #{ticket.id} foi atribuído a você: {ticket.title}",
        )
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=409, detail="Chamado fechado não pode ser alterado"
        )
    record_audit(db, current_user.id, action, "Ticket", ticket.id)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    db.delete(ticket)
    record_audit(db, current_user.id, "DELETE", "Ticket", ticket.id)
    db.commit()

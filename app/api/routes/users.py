from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models import AuditLog, Ticket, TicketComment, User
from app.schemas.auth import UserRead
from app.schemas.user import AdminUserCreate, UserUpdate
from app.services.audit import record_audit
from app.services.user import create_user, get_user_by_email

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserRead, status_code=201)
def create_managed_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    if get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    user = create_user(db, payload.name, payload.email, payload.password)
    user.role = payload.role
    record_audit(db, current_user.id, "CREATE", "User", user.id)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes:
        changes["email"] = str(changes["email"]).lower()
        existing = get_user_by_email(db, changes["email"])
        if existing is not None and existing.id != user.id:
            raise HTTPException(status_code=409, detail="Email já cadastrado")
    if user.id == current_user.id and changes.get("is_active") is False:
        raise HTTPException(
            status_code=409, detail="Você não pode desativar a própria conta"
        )
    if user.id == current_user.id and changes.get("role") is not None:
        raise HTTPException(
            status_code=409, detail="Você não pode alterar a própria role"
        )
    if user.role.value == "ADMIN" and changes.get("is_active") is False:
        admins = (
            db.query(User)
            .filter(User.role == user.role, User.is_active.is_(True))
            .count()
        )
        if admins <= 1:
            raise HTTPException(
                status_code=409,
                detail="O sistema precisa manter um administrador ativo",
            )
    for field, value in changes.items():
        setattr(user, field, value)
    record_audit(db, current_user.id, "UPDATE", "User", user.id, changes)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=409, detail="Você não pode excluir a própria conta"
        )
    has_ticket_history = (
        db.query(Ticket)
        .filter((Ticket.user_id == user.id) | (Ticket.technician_id == user.id))
        .first()
    )
    has_comment_history = (
        db.query(TicketComment).filter(TicketComment.user_id == user.id).first()
    )
    if has_ticket_history or has_comment_history:
        raise HTTPException(
            status_code=409,
            detail="Usuário possui histórico de atendimento; desative a conta em vez de excluí-la",
        )
    db.execute(update(AuditLog).where(AuditLog.user_id == user.id).values(user_id=None))
    db.delete(user)
    db.commit()

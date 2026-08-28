from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models import SlaPolicy, User
from app.models.enums import TicketPriority
from app.schemas.sla import SlaPolicyRead, SlaPolicyUpdate

router = APIRouter(prefix="/sla", tags=["SLA"])


@router.get("", response_model=list[SlaPolicyRead])
def list_sla(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[SlaPolicy]:
    return list(db.scalars(select(SlaPolicy).order_by(SlaPolicy.priority)))


@router.patch("/{priority}", response_model=SlaPolicyRead)
def update_sla(
    priority: TicketPriority,
    payload: SlaPolicyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> SlaPolicy:
    policy = db.get(SlaPolicy, priority)
    if policy is None:
        raise HTTPException(status_code=404, detail="Política de SLA não encontrada")
    policy.resolution_hours = payload.resolution_hours
    db.commit()
    db.refresh(policy)
    return policy

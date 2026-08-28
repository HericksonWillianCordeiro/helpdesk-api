import json

from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit(
    db: Session,
    user_id: int | None,
    action: str,
    entity: str,
    entity_id: int,
    details: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=json.dumps(details) if details else None,
        )
    )

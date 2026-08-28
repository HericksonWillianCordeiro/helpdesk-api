from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification, User
from app.models.enums import UserRole


def notify_user(db: Session, user_id: int, title: str, message: str) -> None:
    db.add(Notification(user_id=user_id, title=title, message=message))


def notify_admins(db: Session, title: str, message: str) -> None:
    admin_ids = db.scalars(
        select(User.id).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
    )
    for admin_id in admin_ids:
        notify_user(db, admin_id, title, message)

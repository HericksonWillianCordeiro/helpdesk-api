from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.models.enums import UserRole
from app.repositories.user import find_by_email, save


def get_user_by_email(db: Session, email: str) -> User | None:
    return find_by_email(db, email)


def create_user(db: Session, name: str, email: str, password: str) -> User:
    user = User(
        name=name.strip(),
        email=email.lower(),
        password_hash=hash_password(password),
        role=UserRole.USER,
    )
    return save(db, user)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user

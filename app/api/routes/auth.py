from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from app.models import RefreshToken, User
from app.schemas.auth import (
    ProfileUpdate,
    RefreshRequest,
    RegisterRequest,
    Token,
    UserRead,
)
from app.services.audit import record_audit
from app.services.user import authenticate_user, create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    if get_user_by_email(db, str(payload.email)) is not None:
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    return create_user(db, payload.name, str(payload.email), payload.password)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Email ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    refresh_token = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return Token(
        access_token=create_access_token(str(user.id)), refresh_token=refresh_token
    )


@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == hash_refresh_token(payload.refresh_token),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        .first()
    )
    if token is None or not token.user.is_active:
        raise HTTPException(
            status_code=401, detail="Refresh token inválido ou expirado"
        )
    token.revoked_at = datetime.now(UTC)
    new_refresh = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=token.user_id,
            token_hash=hash_refresh_token(new_refresh),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return Token(
        access_token=create_access_token(str(token.user_id)),
        refresh_token=new_refresh,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == hash_refresh_token(payload.refresh_token),
            RefreshToken.revoked_at.is_(None),
        )
        .first()
    )
    if token is not None:
        token.revoked_at = datetime.now(UTC)
        db.commit()


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    current_user.name = payload.name.strip()
    record_audit(db, current_user.id, "UPDATE", "User", current_user.id)
    db.commit()
    db.refresh(current_user)
    return current_user

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models import Category, User
from app.schemas.category import CategoryCreate, CategoryRead
from app.services.audit import record_audit

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Category:
    if db.scalar(select(Category).where(Category.name == payload.name.strip())):
        raise HTTPException(status_code=409, detail="Categoria já cadastrada")
    category = Category(name=payload.name.strip(), description=payload.description)
    db.add(category)
    db.flush()
    record_audit(db, _.id, "CREATE", "Category", category.id)
    db.commit()
    db.refresh(category)
    return category


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Category]:
    return list(
        db.scalars(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.name)
        )
    )


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Category:
    category = db.get(Category, category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return category


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    category.name = payload.name.strip()
    category.description = payload.description
    record_audit(db, _.id, "UPDATE", "Category", category.id)
    db.commit()
    db.refresh(category)
    return category

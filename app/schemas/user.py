from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None


class AdminUserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER

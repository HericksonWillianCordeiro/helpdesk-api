from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class CategoryRead(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool

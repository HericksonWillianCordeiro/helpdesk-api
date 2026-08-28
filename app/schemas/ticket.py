from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=10000)
    priority: TicketPriority = TicketPriority.MEDIUM
    category_id: int = Field(gt=0)


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=3, max_length=10000)
    priority: TicketPriority | None = None
    category_id: int | None = Field(default=None, gt=0)


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    resolution_note: str | None = Field(default=None, min_length=3, max_length=5000)


class TicketAssign(BaseModel):
    technician_id: int | None = Field(default=None, gt=0)


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    user_id: int
    technician_id: int | None
    category_id: int
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    sla_due_at: datetime | None
    is_overdue: bool


class TicketPage(BaseModel):
    items: list[TicketRead]
    page: int
    limit: int
    total: int
    pages: int


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentRead(CommentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    user_id: int
    author_name: str
    created_at: datetime

from pydantic import BaseModel, Field

from app.models.enums import TicketPriority


class SlaPolicyRead(BaseModel):
    priority: TicketPriority
    resolution_hours: int


class SlaPolicyUpdate(BaseModel):
    resolution_hours: int = Field(ge=1, le=720)

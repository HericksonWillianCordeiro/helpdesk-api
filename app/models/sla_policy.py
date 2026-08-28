from sqlalchemy import Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import TicketPriority


class SlaPolicy(Base):
    __tablename__ = "sla_policies"

    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority"), primary_key=True
    )
    resolution_hours: Mapped[int] = mapped_column(Integer, nullable=False)

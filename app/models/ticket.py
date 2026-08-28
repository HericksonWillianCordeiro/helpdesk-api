from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TicketPriority, TicketStatus


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"),
        default=TicketStatus.OPEN,
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority"),
        default=TicketPriority.MEDIUM,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_overdue(self) -> bool:
        now = datetime.now(UTC)
        due_at = self.sla_due_at
        if due_at and due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=UTC)
        return bool(
            due_at
            and self.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
            and due_at < now
        )

    user: Mapped["User"] = relationship(
        back_populates="created_tickets", foreign_keys=[user_id]
    )
    technician: Mapped["User | None"] = relationship(
        back_populates="assigned_tickets", foreign_keys=[technician_id]
    )
    category: Mapped["Category"] = relationship(back_populates="tickets")
    comments: Mapped[list["TicketComment"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )

from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class FlaggedEmail(Base):
    __tablename__ = "flagged_emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    scam_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    feedbacks: Mapped[list["UserFeedback"]] = relationship(back_populates="flagged_email")


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    flagged_email_id: Mapped[int] = mapped_column(ForeignKey("flagged_emails.id"))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    confirmed_scam: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    flagged_email: Mapped["FlaggedEmail"] = relationship(back_populates="feedbacks")

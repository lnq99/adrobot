from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_campaign_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    alias: Mapped[str] = mapped_column(String(255), default="")
    geos: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    streams: Mapped[list["Stream"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan")


class Stream(Base):
    __tablename__ = "streams"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    keitaro_stream_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(16), default="offers")  # offers|opaque
    is_dirty: Mapped[bool] = mapped_column(Boolean, default=False)
    published_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    keitaro_signature: Mapped[str] = mapped_column(String(64), default="")
    campaign: Mapped["Campaign"] = relationship(back_populates="streams")
    offers: Mapped[list["OfferState"]] = relationship(
        back_populates="stream", cascade="all, delete-orphan")


class OfferState(Base):
    __tablename__ = "offer_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id"))
    keitaro_offer_id: Mapped[int] = mapped_column(Integer)
    offer_name: Mapped[str] = mapped_column(String(512), default="")
    share: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")   # active|removed
    origin: Mapped[str] = mapped_column(String(16), default="local")    # local|keitaro
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    published_share: Mapped[int] = mapped_column(Integer, default=0)
    stream: Mapped["Stream"] = relationship(back_populates="offers")

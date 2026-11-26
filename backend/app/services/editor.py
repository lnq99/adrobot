from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.services.shares import OfferShare, rebalance
from app import models


def rebalance_stream(stream: models.Stream) -> None:
    shares = [OfferShare(o.keitaro_offer_id, o.status, o.pinned, o.share)
              for o in stream.offers]
    rebalance(shares)
    by_id = {s.offer_id: s for s in shares}
    for o in stream.offers:
        s = by_id[o.keitaro_offer_id]
        o.share = s.share
        o.pinned = s.pinned


def _find(stream: models.Stream, offer_id: int) -> models.OfferState:
    for o in stream.offers:
        if o.keitaro_offer_id == offer_id:
            return o
    raise NotFoundError(f"offer {offer_id} not in stream")


def add_offer(db: Session, stream: models.Stream, *, offer_id: int, offer_name: str) -> None:
    existing = next((o for o in stream.offers if o.keitaro_offer_id == offer_id), None)
    if existing and existing.status == "active":
        raise ValidationError(f"offer {offer_id} already active in stream")
    if existing:
        existing.status = "active"
        existing.origin = "local"
        existing.offer_name = offer_name
    else:
        stream.offers.append(models.OfferState(
            keitaro_offer_id=offer_id, offer_name=offer_name,
            status="active", origin="local", share=0))
    rebalance_stream(stream)
    stream.is_dirty = True
    db.commit()


def remove_offer(db: Session, stream: models.Stream, *, offer_id: int) -> None:
    o = _find(stream, offer_id)
    o.status = "removed"
    o.origin = "local"
    o.pinned = False
    rebalance_stream(stream)
    stream.is_dirty = True
    db.commit()


def bring_back(db: Session, stream: models.Stream, *, offer_id: int) -> None:
    o = _find(stream, offer_id)
    o.status = "active"
    rebalance_stream(stream)
    stream.is_dirty = True
    db.commit()


def pin(db: Session, stream: models.Stream, *, offer_id: int,
        pinned: bool, share: int | None) -> None:
    o = _find(stream, offer_id)
    if o.status != "active":
        raise ValidationError("can only pin an active offer")
    o.pinned = pinned
    if pinned and share is not None and share != o.share:
        o.share = share
        stream.is_dirty = True       # a value change is a publishable change
    rebalance_stream(stream)
    db.commit()

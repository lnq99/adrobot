from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ValidationError
from app.keitaro.base import KeitaroPort, KOffer
from app.services.signature import stream_signature
from app import models


def _active(stream: models.Stream) -> list[models.OfferState]:
    return [o for o in stream.offers if o.status == "active"]


def _snapshot(stream: models.Stream) -> list[dict]:
    return [{"offer_id": o.keitaro_offer_id, "offer_name": o.offer_name,
             "share": o.share, "status": o.status, "origin": o.origin,
             "pinned": o.pinned} for o in stream.offers]


async def push_stream(db: Session, keitaro: KeitaroPort, stream: models.Stream) -> None:
    active = _active(stream)
    total = sum(o.share for o in active)
    if active and total != 100:
        raise ValidationError(f"active shares must total 100, got {total}")

    # conflict check: compare stored signature against Keitaro's current state
    if stream.keitaro_signature:
        kstreams = await keitaro.get_campaign_streams(stream.campaign.keitaro_campaign_id)
        current = next((s for s in kstreams if s.id == stream.keitaro_stream_id), None)
        if current is not None and stream_signature(current) != stream.keitaro_signature:
            raise ConflictError("Keitaro changed underneath; re-fetch before pushing")

    koffers = [KOffer(o.keitaro_offer_id, o.share, "active") for o in active]
    updated = await keitaro.update_stream_offers(stream.keitaro_stream_id, koffers)

    for o in stream.offers:
        o.published_share = o.share if o.status == "active" else 0
    stream.published_snapshot = _snapshot(stream)
    stream.keitaro_signature = stream_signature(updated)
    stream.is_dirty = False
    db.commit()


def cancel_stream(db: Session, stream: models.Stream) -> None:
    snap = {s["offer_id"]: s for s in (stream.published_snapshot or [])}
    # drop offers that were never published; restore the rest
    for o in list(stream.offers):
        if o.keitaro_offer_id not in snap:
            stream.offers.remove(o)
            db.delete(o)
        else:
            s = snap[o.keitaro_offer_id]
            o.share = s["share"]
            o.status = s["status"]
            o.origin = s["origin"]
            o.pinned = s["pinned"]
            o.published_share = s["share"] if s["status"] == "active" else 0
    stream.is_dirty = False
    db.commit()

from app.schemas import StreamOut
from app import models


def stream_to_out(s: models.Stream) -> StreamOut:
    """Single source of truth for serializing a Stream to the API shape."""
    return StreamOut(
        id=s.id, keitaro_stream_id=s.keitaro_stream_id, position=s.position,
        kind=s.kind, is_dirty=s.is_dirty,
        offers=[{"keitaro_offer_id": o.keitaro_offer_id, "offer_name": o.offer_name,
                 "share": o.share, "status": o.status, "origin": o.origin,
                 "pinned": o.pinned} for o in s.offers])

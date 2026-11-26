from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_keitaro
from app.core.errors import NotFoundError, ValidationError
from app.schemas import AddOfferIn, PinIn, StreamOut
from app.services import editor
from app.services.publisher import cancel_stream, push_stream
from app import models

router = APIRouter(prefix="/api/streams", tags=["streams"])


def _get(db: Session, stream_id: int) -> models.Stream:
    s = db.get(models.Stream, stream_id)
    if s is None:
        raise NotFoundError(f"stream {stream_id} not found")
    if s.kind != "offers":
        raise ValidationError("stream has no editable offers")
    return s


def _out(s: models.Stream) -> StreamOut:
    return StreamOut(
        id=s.id, keitaro_stream_id=s.keitaro_stream_id, position=s.position,
        kind=s.kind, is_dirty=s.is_dirty,
        offers=[{"keitaro_offer_id": o.keitaro_offer_id, "offer_name": o.offer_name,
                 "share": o.share, "status": o.status, "origin": o.origin,
                 "pinned": o.pinned} for o in s.offers])


@router.post("/{stream_id}/offers", response_model=StreamOut)
async def add(stream_id: int, body: AddOfferIn, db: Session = Depends(get_db),
              keitaro=Depends(get_keitaro)) -> StreamOut:
    s = _get(db, stream_id)
    offer = await keitaro.get_offer(body.offer_id)
    if offer is None:
        raise ValidationError(f"offer {body.offer_id} not found")
    editor.add_offer(db, s, offer_id=body.offer_id, offer_name=offer.get("name", ""))
    return _out(s)


@router.delete("/{stream_id}/offers/{offer_id}", response_model=StreamOut)
def remove(stream_id: int, offer_id: int, db: Session = Depends(get_db)) -> StreamOut:
    s = _get(db, stream_id)
    editor.remove_offer(db, s, offer_id=offer_id)
    return _out(s)


@router.post("/{stream_id}/offers/{offer_id}/bring-back", response_model=StreamOut)
def bring_back(stream_id: int, offer_id: int, db: Session = Depends(get_db)) -> StreamOut:
    s = _get(db, stream_id)
    editor.bring_back(db, s, offer_id=offer_id)
    return _out(s)


@router.post("/{stream_id}/offers/{offer_id}/pin", response_model=StreamOut)
def pin(stream_id: int, offer_id: int, body: PinIn,
        db: Session = Depends(get_db)) -> StreamOut:
    s = _get(db, stream_id)
    editor.pin(db, s, offer_id=offer_id, pinned=body.pinned, share=body.share)
    return _out(s)


@router.post("/{stream_id}/push", response_model=StreamOut)
async def push(stream_id: int, db: Session = Depends(get_db),
               keitaro=Depends(get_keitaro)) -> StreamOut:
    s = _get(db, stream_id)
    await push_stream(db, keitaro, s)
    return _out(s)


@router.post("/{stream_id}/cancel", response_model=StreamOut)
def cancel(stream_id: int, db: Session = Depends(get_db)) -> StreamOut:
    s = _get(db, stream_id)
    cancel_stream(db, s)
    return _out(s)

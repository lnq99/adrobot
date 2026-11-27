import time

from fastapi import APIRouter, Depends

from app.api.deps import get_keitaro
from app.keitaro.fake import FakeKeitaro

router = APIRouter(prefix="/api/offers", tags=["offers"])

# Keitaro's /offers returns every offer; cache it briefly so typing a search
# doesn't re-download the whole catalogue each time. Skipped for the in-memory
# fake (instant, and keeps tests isolated).
_CACHE_TTL = 5.0
_offers_cache: dict = {"at": 0.0, "data": None}


async def _all_offers(keitaro) -> list[dict]:
    if isinstance(keitaro, FakeKeitaro):
        return await keitaro.list_offers()
    now = time.monotonic()
    if _offers_cache["data"] is None or now - _offers_cache["at"] > _CACHE_TTL:
        _offers_cache["data"] = await keitaro.list_offers()
        _offers_cache["at"] = now
    return _offers_cache["data"]


@router.get("")
async def search_offers(q: str = "", keitaro=Depends(get_keitaro)) -> list[dict]:
    offers = await _all_offers(keitaro)
    # Hide offers Keitaro has deleted/archived (when a state field is present).
    offers = [o for o in offers if o.get("state", "active") != "deleted"]
    if q:
        ql = q.lower()
        offers = [o for o in offers
                  if ql in str(o.get("id")) or ql in o.get("name", "").lower()]
        # Exact id match ranks first; the rest keep their order (stable sort).
        offers = sorted(offers, key=lambda o: str(o.get("id")) != q)
    return offers[:50]

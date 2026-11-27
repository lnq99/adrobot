from fastapi import APIRouter, Depends

from app.api.deps import get_keitaro

router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("")
async def search_offers(q: str = "", keitaro=Depends(get_keitaro)) -> list[dict]:
    offers = await keitaro.list_offers()
    # Hide offers Keitaro has deleted/archived (when a state field is present).
    offers = [o for o in offers if o.get("state", "active") != "deleted"]
    if q:
        ql = q.lower()
        offers = [o for o in offers
                  if ql in str(o.get("id")) or ql in o.get("name", "").lower()]
        # Exact id match ranks first; the rest keep their order (stable sort).
        offers = sorted(offers, key=lambda o: str(o.get("id")) != q)
    return offers[:50]

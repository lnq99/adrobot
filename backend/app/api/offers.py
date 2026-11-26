from fastapi import APIRouter, Depends

from app.api.deps import get_keitaro

router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("")
async def search_offers(q: str = "", keitaro=Depends(get_keitaro)) -> list[dict]:
    offers = await keitaro.list_offers()
    if q:
        ql = q.lower()
        offers = [o for o in offers
                  if ql in str(o.get("id")) or ql in o.get("name", "").lower()]
    return offers[:50]

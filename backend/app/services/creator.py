import pycountry

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ValidationError
from app.keitaro.base import KeitaroPort
from app import models


def _validate_geos(geos: list[str]) -> list[str]:
    if not geos:
        raise ValidationError("at least one geo is required")
    out = []
    for g in geos:
        code = g.strip().upper()
        if not pycountry.countries.get(alpha_2=code):
            raise ValidationError(f"invalid ISO country code: {g}")
        out.append(code)
    return out


async def create_campaign(db: Session, keitaro: KeitaroPort, *,
                          name: str, geos: list[str], offer_id: int) -> models.Campaign:
    geos = _validate_geos(geos)
    if await keitaro.get_offer(offer_id) is None:
        raise ValidationError(f"offer {offer_id} not found in Keitaro")

    kcamp = await keitaro.create_campaign(
        name=name, group_id=settings.keitaro_group_id,
        traffic_source_id=settings.keitaro_source_id,
        domain_id=settings.keitaro_domain_id)

    try:
        s1 = await keitaro.create_stream({
            "campaign_id": kcamp.id, "name": f"Geo {'/'.join(geos)}",
            "type": "regular", "schema": "redirect",
            "action_type": "http", "action_payload": "https://google.com",
            "filters": [{"name": "country", "mode": "accept", "payload": geos}]})
        s2 = await keitaro.create_stream({
            "campaign_id": kcamp.id, "name": "Offers",
            "type": "default", "schema": "landings",
            "offers": [{"offer_id": offer_id, "share": 100, "state": "active"}]})
    except Exception:
        await keitaro.delete_campaign(kcamp.id)
        raise

    campaign = models.Campaign(keitaro_campaign_id=kcamp.id, name=kcamp.name,
                               alias=kcamp.alias, geos=geos)
    db.add(campaign)
    db.flush()

    campaign.streams.append(models.Stream(
        keitaro_stream_id=s1.id, position=s1.position, kind="opaque"))
    offers_stream = models.Stream(
        keitaro_stream_id=s2.id, position=s2.position, kind="offers")
    offers_stream.offers.append(models.OfferState(
        keitaro_offer_id=offer_id, share=100, status="active",
        published_share=100))
    campaign.streams.append(offers_stream)
    db.commit()
    return campaign

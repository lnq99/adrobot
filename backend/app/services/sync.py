from sqlalchemy.orm import Session

from app.keitaro.base import KeitaroPort
from app.services.editor import rebalance_stream
from app.services.signature import stream_signature
from app import models


async def fetch_campaign(db: Session, keitaro: KeitaroPort,
                         campaign: models.Campaign) -> models.Campaign:
    kstreams = await keitaro.get_campaign_streams(campaign.keitaro_campaign_id)
    local_by_kid = {s.keitaro_stream_id: s for s in campaign.streams}

    for ks in kstreams:
        local = local_by_kid.get(ks.id)
        if local is None:
            local = models.Stream(
                keitaro_stream_id=ks.id, position=ks.position,
                kind="offers" if ks.schema == "landings" else "opaque")
            campaign.streams.append(local)
        local.position = ks.position

        if local.kind != "offers":
            continue

        local.keitaro_signature = stream_signature(ks)
        upstream_ids = {o.offer_id for o in ks.offers}
        known = {o.keitaro_offer_id: o for o in local.offers}

        # reverse-sync: offers we knew but are gone upstream -> REM (unless already removed)
        any_rem = False
        for oid, o in known.items():
            if o.status == "active" and oid not in upstream_ids:
                o.status = "removed"
                o.origin = "keitaro"
                o.pinned = False
                o.share = 0
                any_rem = True

        # if any offer was flipped to REM, rebalance so active offers still total 100
        if any_rem:
            rebalance_stream(local)
            local.is_dirty = True

    db.commit()
    return campaign

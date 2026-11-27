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

        # forward-sync: offers added directly in Keitaro that we don't know yet ->
        # import them as active, so a later push does not silently delete them.
        any_added = False
        for ko in ks.offers:
            if ko.offer_id not in known:
                offer = await keitaro.get_offer(ko.offer_id)
                local.offers.append(models.OfferState(
                    keitaro_offer_id=ko.offer_id,
                    offer_name=(offer or {}).get("name", ""),
                    status="active", origin="keitaro", share=0))
                any_added = True

        # reverse-sync: offers we knew but are gone upstream -> removed (REM)
        any_rem = False
        for oid, o in known.items():
            if o.status == "active" and oid not in upstream_ids:
                o.status = "removed"
                o.origin = "keitaro"
                o.pinned = False
                o.share = 0
                any_rem = True

        # a changed offer set means the local draft must re-total 100
        if any_added or any_rem:
            rebalance_stream(local)
            local.is_dirty = True

        # Record what Keitaro currently holds so Cancel has a baseline to restore
        # to (without this, Cancel before the first push would wipe every offer).
        local_offer = {o.keitaro_offer_id: o for o in local.offers}
        local.published_snapshot = [
            {"offer_id": ko.offer_id,
             "offer_name": local_offer[ko.offer_id].offer_name if ko.offer_id in local_offer else "",
             "share": ko.share, "status": "active",
             "origin": local_offer[ko.offer_id].origin if ko.offer_id in local_offer else "keitaro",
             "pinned": False}
            for ko in ks.offers
        ]
        for o in local.offers:
            if o.status == "active":
                o.published_share = next(
                    (ko.share for ko in ks.offers if ko.offer_id == o.keitaro_offer_id), 0)

    db.commit()
    return campaign

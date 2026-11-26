import pytest

from app.services.creator import create_campaign
from app.services.sync import fetch_campaign
from app import models


@pytest.mark.asyncio
async def test_fetch_marks_missing_offer_as_rem(db, keitaro):
    camp = await create_campaign(db, keitaro, name="test_quang_s",
                                 geos=["GM"], offer_id=18001)
    offers_stream = next(s for s in camp.streams if s.kind == "offers")
    # add a 2nd offer and publish it directly into the fake (simulate prior push)
    from app.keitaro.base import KOffer
    await keitaro.update_stream_offers(
        offers_stream.keitaro_stream_id, [KOffer(18001, 50), KOffer(18002, 50)])
    # our local DB also knows about 18002 as active
    offers_stream.offers.append(models.OfferState(
        keitaro_offer_id=18002, status="active", share=50, published_share=50))
    db.commit()
    # admin deletes 18002 from Keitaro
    keitaro.admin_remove_offer(offers_stream.keitaro_stream_id, 18002)

    await fetch_campaign(db, keitaro, camp)
    rem = next(o for o in offers_stream.offers if o.keitaro_offer_id == 18002)
    assert rem.status == "removed" and rem.origin == "keitaro"


@pytest.mark.asyncio
async def test_fetch_preserves_opaque_streams(db, keitaro):
    camp = await create_campaign(db, keitaro, name="test_quang_s2",
                                 geos=["GM"], offer_id=18001)
    await fetch_campaign(db, keitaro, camp)
    kinds = sorted(s.kind for s in camp.streams)
    assert kinds == ["offers", "opaque"]


@pytest.mark.asyncio
async def test_push_succeeds_after_rem_fetch(db, keitaro):
    """After fetch marks an offer REM, surviving active offers must still total 100
    so that push_stream succeeds without ValidationError."""
    from app.services import editor
    from app.services.publisher import push_stream
    from app.keitaro.base import KOffer

    camp = await create_campaign(db, keitaro, name="test_quang_s3",
                                 geos=["GM"], offer_id=18001)
    offers_stream = next(s for s in camp.streams if s.kind == "offers")

    # Add a 2nd offer locally and push so Keitaro has 2 offers 50/50
    editor.add_offer(db, offers_stream, offer_id=18002, offer_name="B")
    await push_stream(db, keitaro, offers_stream)

    # Admin removes offer 18002 directly from Keitaro
    keitaro.admin_remove_offer(offers_stream.keitaro_stream_id, 18002)

    # Fetch detects the removal and marks 18002 as REM
    await fetch_campaign(db, keitaro, camp)

    # Surviving active offers must still total 100
    active = [o for o in offers_stream.offers if o.status == "active"]
    total = sum(o.share for o in active)
    assert total == 100, f"active shares should total 100 after REM fetch, got {total}"
    assert offers_stream.is_dirty is True

    # push_stream must succeed (no ValidationError)
    await push_stream(db, keitaro, offers_stream)

    # Keitaro ends with only the surviving offer
    kstreams = await keitaro.get_campaign_streams(camp.keitaro_campaign_id)
    pushed = next(s for s in kstreams if s.id == offers_stream.keitaro_stream_id)
    assert [o.offer_id for o in pushed.offers] == [18001]

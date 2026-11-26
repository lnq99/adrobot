import pytest

from app.services import editor
from app.services.creator import create_campaign
from app import models


async def _campaign_with_offers_stream(db, keitaro, n=1):
    camp = await create_campaign(db, keitaro, name="test_quang_e",
                                 geos=["GM"], offer_id=18001)
    stream = next(s for s in camp.streams if s.kind == "offers")
    return camp, stream


@pytest.mark.asyncio
async def test_add_offer_rebalances_and_dirties(db, keitaro):
    _, stream = await _campaign_with_offers_stream(db, keitaro)
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    shares = sorted(o.share for o in stream.offers if o.status == "active")
    assert shares == [50, 50]
    assert stream.is_dirty is True


@pytest.mark.asyncio
async def test_remove_offer_grays_and_zeros(db, keitaro):
    _, stream = await _campaign_with_offers_stream(db, keitaro)
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    editor.remove_offer(db, stream, offer_id=18002)
    removed = next(o for o in stream.offers if o.keitaro_offer_id == 18002)
    assert removed.status == "removed" and removed.origin == "local"
    assert removed.share == 0
    active = [o for o in stream.offers if o.status == "active"]
    assert active[0].share == 100


@pytest.mark.asyncio
async def test_bring_back_reactivates(db, keitaro):
    _, stream = await _campaign_with_offers_stream(db, keitaro)
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    editor.remove_offer(db, stream, offer_id=18002)
    editor.bring_back(db, stream, offer_id=18002)
    assert all(o.status == "active" for o in stream.offers)
    assert sorted(o.share for o in stream.offers) == [50, 50]


@pytest.mark.asyncio
async def test_add_offer_refreshes_name_on_reactivation(db, keitaro):
    """Re-adding a removed offer must update offer_name to the new name."""
    _, stream = await _campaign_with_offers_stream(db, keitaro)
    editor.add_offer(db, stream, offer_id=18002, offer_name="OldName")
    editor.remove_offer(db, stream, offer_id=18002)
    # Re-add with a new name
    editor.add_offer(db, stream, offer_id=18002, offer_name="NewName")
    reactivated = next(o for o in stream.offers if o.keitaro_offer_id == 18002)
    assert reactivated.status == "active"
    assert reactivated.offer_name == "NewName", (
        f"expected offer_name='NewName', got '{reactivated.offer_name}'"
    )


@pytest.mark.asyncio
async def test_pin_sets_value_and_dirties_only_on_value(db, keitaro):
    _, stream = await _campaign_with_offers_stream(db, keitaro)
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    editor.add_offer(db, stream, offer_id=18003, offer_name="C")
    stream.is_dirty = False
    # pin toggle without value -> not dirty
    editor.pin(db, stream, offer_id=18001, pinned=True, share=None)
    assert stream.is_dirty is False
    # pin with explicit value -> dirty
    editor.pin(db, stream, offer_id=18001, pinned=True, share=40)
    pinned = next(o for o in stream.offers if o.keitaro_offer_id == 18001)
    assert pinned.pinned and pinned.share == 40
    others = sorted(o.share for o in stream.offers if not o.pinned)
    assert others == [30, 30]
    assert stream.is_dirty is True

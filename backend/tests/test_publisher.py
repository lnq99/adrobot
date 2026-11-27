import pytest

from app.core.errors import ConflictError
from app.services import editor
from app.services.creator import create_campaign
from app.services.publisher import push_stream, cancel_stream
from app.keitaro.base import KOffer


async def _stream_with_two(db, keitaro):
    camp = await create_campaign(db, keitaro, name="test_quang_p",
                                 geos=["GM"], offer_id=18001)
    stream = next(s for s in camp.streams if s.kind == "offers")
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    return camp, stream


@pytest.mark.asyncio
async def test_push_sends_active_offers_and_clears_dirty(db, keitaro):
    _, stream = await _stream_with_two(db, keitaro)
    await push_stream(db, keitaro, stream)
    ks = (await keitaro.get_campaign_streams(stream.campaign.keitaro_campaign_id))
    pushed = next(s for s in ks if s.id == stream.keitaro_stream_id)
    assert sorted(o.offer_id for o in pushed.offers) == [18001, 18002]
    assert stream.is_dirty is False
    assert all(o.published_share == o.share for o in stream.offers if o.status == "active")


@pytest.mark.asyncio
async def test_push_conflict_when_keitaro_changed(db, keitaro):
    _, stream = await _stream_with_two(db, keitaro)
    await push_stream(db, keitaro, stream)
    # someone edits Keitaro directly -> signature diverges
    await keitaro.update_stream_offers(stream.keitaro_stream_id, [KOffer(18001, 100)])
    editor.add_offer(db, stream, offer_id=18003, offer_name="C")
    with pytest.raises(ConflictError):
        await push_stream(db, keitaro, stream)


@pytest.mark.asyncio
async def test_cancel_before_push_keeps_created_offer(db, keitaro):
    """Cancel before any push must not wipe the stream: the just-created offer
    (already live in Keitaro) has to survive."""
    camp = await create_campaign(db, keitaro, name="test_quang_cancel",
                                 geos=["GM"], offer_id=18001)
    stream = next(s for s in camp.streams if s.kind == "offers")
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")  # unpublished edit
    cancel_stream(db, stream)
    ids = sorted(o.keitaro_offer_id for o in stream.offers if o.status == "active")
    assert ids == [18001]  # original offer kept, unpublished 18002 dropped


@pytest.mark.asyncio
async def test_cancel_restores_published_snapshot(db, keitaro):
    _, stream = await _stream_with_two(db, keitaro)
    await push_stream(db, keitaro, stream)       # snapshot = {18001,18002}
    editor.add_offer(db, stream, offer_id=18003, offer_name="C")
    cancel_stream(db, stream)
    ids = sorted(o.keitaro_offer_id for o in stream.offers if o.status == "active")
    assert ids == [18001, 18002]
    assert stream.is_dirty is False

# backend/tests/test_walkthrough.py
import pytest

from app.services import editor
from app.services.creator import create_campaign
from app.services.publisher import push_stream, cancel_stream
from app.services.sync import fetch_campaign


def active_shares(stream):
    return sorted(o.share for o in stream.offers if o.status == "active")


@pytest.mark.asyncio
async def test_full_walkthrough(db, keitaro):
    # 1. create campaign -> 2 streams, offer @100
    camp = await create_campaign(db, keitaro, name="test_quang_w",
                                 geos=["GM", "FR"], offer_id=18001)
    stream = next(s for s in camp.streams if s.kind == "offers")
    assert active_shares(stream) == [100]

    # 2-3. grow to 3 then 4 offers
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    editor.add_offer(db, stream, offer_id=18003, offer_name="C")
    assert active_shares(stream) == [33, 33, 34]
    editor.add_offer(db, stream, offer_id=18004, offer_name="D")
    assert active_shares(stream) == [25, 25, 25, 25]
    assert stream.is_dirty is True

    # 4. push -> not dirty, all four live
    await push_stream(db, keitaro, stream)
    assert stream.is_dirty is False

    # 5. add then cancel -> the added-but-unpublished offer vanishes
    editor.add_offer(db, stream, offer_id=18005, offer_name="E")
    assert active_shares(stream) == [20, 20, 20, 20, 20]
    cancel_stream(db, stream)
    assert active_shares(stream) == [25, 25, 25, 25]
    assert 18005 not in [o.keitaro_offer_id for o in stream.offers]

    # 6. remove -> gray/0, push -> gone upstream but archived locally
    editor.remove_offer(db, stream, offer_id=18004)
    await push_stream(db, keitaro, stream)
    archived = next(o for o in stream.offers if o.keitaro_offer_id == 18004)
    assert archived.status == "removed" and archived.share == 0

    # 7. bring back -> active -> push
    editor.bring_back(db, stream, offer_id=18004)
    await push_stream(db, keitaro, stream)
    assert 18004 in [o.keitaro_offer_id for o in stream.offers if o.status == "active"]

    # 8. admin deletes an offer in Keitaro -> fetch -> REM
    keitaro.admin_remove_offer(stream.keitaro_stream_id, 18003)
    await fetch_campaign(db, keitaro, camp)
    rem = next(o for o in stream.offers if o.keitaro_offer_id == 18003)
    assert rem.status == "removed" and rem.origin == "keitaro"

    # 9. pin at 25 -> others fill to 100
    editor.pin(db, stream, offer_id=18001, pinned=True, share=25)
    pinned = next(o for o in stream.offers if o.keitaro_offer_id == 18001)
    assert pinned.share == 25
    assert sum(o.share for o in stream.offers if o.status == "active") == 100

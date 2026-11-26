import pytest

from app.keitaro.base import KOffer
from app.keitaro.fake import FakeKeitaro


@pytest.mark.asyncio
async def test_create_campaign_and_streams():
    k = FakeKeitaro(offers={18001: {"id": 18001, "name": "Off A"}})
    camp = await k.create_campaign("test_x_1", group_id=10332,
                                   traffic_source_id=836, domain_id=1813)
    assert camp.id > 0 and camp.alias

    s = await k.create_stream({"campaign_id": camp.id, "name": "Offers",
                               "schema": "landings",
                               "offers": [{"offer_id": 18001, "share": 100, "state": "active"}]})
    streams = await k.get_campaign_streams(camp.id)
    assert [st.id for st in streams] == [s.id]
    assert streams[0].offers[0].offer_id == 18001


@pytest.mark.asyncio
async def test_update_stream_offers_replaces():
    k = FakeKeitaro(offers={1: {"id": 1, "name": "A"}, 2: {"id": 2, "name": "B"}})
    camp = await k.create_campaign("c", 1, 1, 1)
    s = await k.create_stream({"campaign_id": camp.id, "name": "o", "schema": "landings",
                               "offers": [{"offer_id": 1, "share": 100, "state": "active"}]})
    await k.update_stream_offers(s.id, [KOffer(2, 100)])
    streams = await k.get_campaign_streams(camp.id)
    assert [o.offer_id for o in streams[0].offers] == [2]

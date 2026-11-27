import pytest

from app.api.offers import search_offers
from app.keitaro.fake import FakeKeitaro


@pytest.mark.asyncio
async def test_offer_search_by_number_puts_exact_match_first():
    # Both offers match the query "18002" (one by exact id, one by substring),
    # but the exact id must rank first.
    fake = FakeKeitaro(offers={
        180025: {"id": 180025, "name": "18002 lookalike"},
        18002: {"id": 18002, "name": "Alpha"},
    })
    out = await search_offers(q="18002", keitaro=fake)
    assert [o["id"] for o in out][0] == 18002


@pytest.mark.asyncio
async def test_offer_search_by_words():
    fake = FakeKeitaro(offers={
        18001: {"id": 18001, "name": "Crypto Leads"},
        18002: {"id": 18002, "name": "Insurance US"},
    })
    out = await search_offers(q="insurance", keitaro=fake)
    assert [o["id"] for o in out] == [18002]


@pytest.mark.asyncio
async def test_offer_search_hides_deleted():
    fake = FakeKeitaro(offers={
        18001: {"id": 18001, "name": "Live", "state": "active"},
        18002: {"id": 18002, "name": "Gone", "state": "deleted"},
    })
    ids = {o["id"] for o in await search_offers(q="", keitaro=fake)}
    assert 18001 in ids and 18002 not in ids


@pytest.mark.asyncio
async def test_offer_search_respects_limit():
    fake = FakeKeitaro(offers={i: {"id": i, "name": "offer"} for i in range(1000, 1100)})
    out = await search_offers(q="offer", keitaro=fake)
    assert len(out) <= 50

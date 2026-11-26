import pytest

from app.core.errors import ValidationError
from app.services.creator import create_campaign
from app import models


@pytest.mark.asyncio
async def test_creates_campaign_with_two_streams(db, keitaro):
    camp = await create_campaign(db, keitaro, name="test_quang_c1",
                                 geos=["GM"], offer_id=18001)
    assert camp.keitaro_campaign_id > 0
    streams = db.query(models.Stream).filter_by(campaign_id=camp.id).all()
    assert len(streams) == 2
    offers_stream = next(s for s in streams if s.kind == "offers")
    assert [o.keitaro_offer_id for o in offers_stream.offers] == [18001]
    assert offers_stream.offers[0].share == 100


@pytest.mark.asyncio
async def test_rejects_unknown_offer(db, keitaro):
    with pytest.raises(ValidationError):
        await create_campaign(db, keitaro, name="test_quang_c2",
                              geos=["GM"], offer_id=99999)


@pytest.mark.asyncio
async def test_rejects_invalid_geo(db, keitaro):
    with pytest.raises(ValidationError):
        await create_campaign(db, keitaro, name="test_quang_c3",
                              geos=["ZZ"], offer_id=18001)


@pytest.mark.asyncio
async def test_rollback_on_stream_failure(db, monkeypatch, keitaro):
    async def boom(payload):
        raise RuntimeError("stream fail")
    monkeypatch.setattr(keitaro, "create_stream", boom)
    with pytest.raises(Exception):
        await create_campaign(db, keitaro, name="test_quang_c4",
                              geos=["GM"], offer_id=18001)
    # campaign must have been deleted upstream (none left in fake)
    assert keitaro._campaigns == {}

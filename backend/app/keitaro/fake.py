from itertools import count

from app.core.errors import NotFoundError
from app.keitaro.base import KCampaign, KOffer, KStream


class FakeKeitaro:
    """In-memory stand-in for the Keitaro Admin API, used in tests."""

    def __init__(self, offers: dict[int, dict] | None = None):
        self._offers = offers or {}
        self._campaigns: dict[int, KCampaign] = {}
        self._streams: dict[int, KStream] = {}
        self._stream_campaign: dict[int, int] = {}
        self._ids = count(1)

    async def get_offer(self, offer_id: int) -> dict | None:
        return self._offers.get(offer_id)

    async def list_offers(self) -> list[dict]:
        return list(self._offers.values())

    async def create_campaign(self, name, group_id, traffic_source_id, domain_id) -> KCampaign:
        cid = next(self._ids)
        camp = KCampaign(id=cid, name=name, alias=f"alias{cid}")
        self._campaigns[cid] = camp
        return camp

    async def delete_campaign(self, campaign_id: int) -> None:
        self._campaigns.pop(campaign_id, None)
        for sid in [s for s, c in self._stream_campaign.items() if c == campaign_id]:
            self._streams.pop(sid, None)
            self._stream_campaign.pop(sid, None)

    async def create_stream(self, payload: dict) -> KStream:
        sid = next(self._ids)
        cid = payload["campaign_id"]
        offers = [KOffer(o["offer_id"], o["share"], o.get("state", "active"))
                  for o in payload.get("offers", [])]
        position = sum(1 for c in self._stream_campaign.values() if c == cid) + 1
        stream = KStream(id=sid, name=payload["name"], position=position,
                         schema=payload.get("schema", "landings"), offers=offers)
        self._streams[sid] = stream
        self._stream_campaign[sid] = cid
        return stream

    async def get_campaign_streams(self, campaign_id: int) -> list[KStream]:
        sids = [s for s, c in self._stream_campaign.items() if c == campaign_id]
        return sorted((self._streams[s] for s in sids), key=lambda st: st.position)

    async def update_stream_offers(self, stream_id: int, offers: list[KOffer]) -> KStream:
        if stream_id not in self._streams:
            raise NotFoundError(f"stream {stream_id} not found")
        self._streams[stream_id].offers = list(offers)
        return self._streams[stream_id]

    # test helper: simulate an admin deleting an offer from a stream directly
    def admin_remove_offer(self, stream_id: int, offer_id: int) -> None:
        st = self._streams[stream_id]
        st.offers = [o for o in st.offers if o.offer_id != offer_id]

import httpx

from app.core.config import settings
from app.core.errors import NotFoundError, UpstreamError
from app.keitaro.base import KCampaign, KOffer, KStream


def _to_stream(d: dict) -> KStream:
    return KStream(
        id=d["id"], name=d.get("name", ""), position=d.get("position", 0),
        schema=d.get("schema", ""),
        offers=[KOffer(o["offer_id"], o.get("share", 0), o.get("state", "active"))
                for o in d.get("offers", [])],
    )


class KeitaroClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self._base = (base_url or settings.keitaro_base_url).rstrip("/")
        self._headers = {"Api-Key": api_key or settings.keitaro_api_key}

    async def _request(self, method: str, path: str, json: dict | None = None) -> httpx.Response:
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                resp = await client.request(method, f"{self._base}{path}",
                                            headers=self._headers, json=json)
            except httpx.HTTPError as exc:
                raise UpstreamError(f"Keitaro request failed: {exc!s}") from exc
        if resp.status_code == 404:
            raise NotFoundError(f"Keitaro 404 for {path}")
        if resp.status_code >= 500:
            raise UpstreamError(f"Keitaro {resp.status_code} for {path}")
        if resp.status_code >= 400:
            raise UpstreamError(f"Keitaro {resp.status_code}: {resp.text[:200]}")
        return resp

    async def get_offer(self, offer_id: int) -> dict | None:
        try:
            return (await self._request("GET", f"/offers/{offer_id}")).json()
        except NotFoundError:
            return None

    async def list_offers(self) -> list[dict]:
        return (await self._request("GET", "/offers")).json()

    async def create_campaign(self, name, group_id, traffic_source_id, domain_id) -> KCampaign:
        d = (await self._request("POST", "/campaigns", json={
            "name": name, "type": "position", "group_id": group_id,
            "traffic_source_id": traffic_source_id, "domain_id": domain_id,
            "state": "active"})).json()
        return KCampaign(id=d["id"], name=d["name"], alias=d.get("alias", ""))

    async def delete_campaign(self, campaign_id: int) -> None:
        await self._request("DELETE", f"/campaigns/{campaign_id}")

    async def create_stream(self, payload: dict) -> KStream:
        return _to_stream((await self._request("POST", "/streams", json=payload)).json())

    async def get_campaign_streams(self, campaign_id: int) -> list[KStream]:
        data = (await self._request("GET", f"/campaigns/{campaign_id}/streams")).json()
        return [_to_stream(s) for s in data]

    async def update_stream_offers(self, stream_id: int, offers: list[KOffer]) -> KStream:
        payload = {"offers": [{"offer_id": o.offer_id, "share": o.share,
                               "state": o.state} for o in offers]}
        return _to_stream((await self._request("PUT", f"/streams/{stream_id}",
                                                json=payload)).json())

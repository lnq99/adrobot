from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class KOffer:
    offer_id: int
    share: int
    state: str = "active"       # Keitaro-side state


@dataclass
class KStream:
    id: int
    name: str
    position: int
    schema: str                 # "landings" (offers) | "redirect" | ...
    offers: list[KOffer] = field(default_factory=list)


@dataclass
class KCampaign:
    id: int
    name: str
    alias: str


class KeitaroPort(Protocol):
    async def get_offer(self, offer_id: int) -> dict | None: ...
    async def list_offers(self) -> list[dict]: ...
    async def create_campaign(self, name: str, group_id: int,
                              traffic_source_id: int, domain_id: int) -> KCampaign: ...
    async def delete_campaign(self, campaign_id: int) -> None: ...
    async def create_stream(self, payload: dict) -> KStream: ...
    async def get_campaign_streams(self, campaign_id: int) -> list[KStream]: ...
    async def update_stream_offers(self, stream_id: int, offers: list[KOffer]) -> KStream: ...

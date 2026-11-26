from pydantic import BaseModel


class CreateCampaignIn(BaseModel):
    name: str
    geos: list[str]
    offer_id: int


class OfferOut(BaseModel):
    keitaro_offer_id: int
    offer_name: str
    share: int
    status: str
    origin: str
    pinned: bool


class StreamOut(BaseModel):
    id: int
    keitaro_stream_id: int
    position: int
    kind: str
    is_dirty: bool
    offers: list[OfferOut]


class CampaignOut(BaseModel):
    id: int
    keitaro_campaign_id: int
    name: str
    alias: str
    geos: list[str]


class AddOfferIn(BaseModel):
    offer_id: int


class PinIn(BaseModel):
    pinned: bool
    share: int | None = None

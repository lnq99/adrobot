from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_keitaro
from app.api._serialize import stream_to_out
from app.core.errors import NotFoundError
from app.schemas import CampaignOut, CreateCampaignIn, StreamOut
from app.services.creator import create_campaign
from app.services.sync import fetch_campaign
from app import models

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _campaign_out(c: models.Campaign) -> CampaignOut:
    return CampaignOut(id=c.id, keitaro_campaign_id=c.keitaro_campaign_id,
                       name=c.name, alias=c.alias, geos=c.geos)


def _streams_out(c: models.Campaign) -> list[StreamOut]:
    return [stream_to_out(s) for s in c.streams]


def _get(db: Session, campaign_id: int) -> models.Campaign:
    c = db.get(models.Campaign, campaign_id)
    if c is None:
        raise NotFoundError(f"campaign {campaign_id} not found")
    return c


@router.post("", response_model=CampaignOut)
async def create(body: CreateCampaignIn, db: Session = Depends(get_db),
                 keitaro=Depends(get_keitaro)) -> CampaignOut:
    c = await create_campaign(db, keitaro, name=body.name, geos=body.geos,
                              offer_id=body.offer_id)
    return _campaign_out(c)


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)) -> list[CampaignOut]:
    return [_campaign_out(c) for c in db.query(models.Campaign).all()]


@router.get("/{campaign_id}/streams", response_model=list[StreamOut])
def get_streams(campaign_id: int, db: Session = Depends(get_db)) -> list[StreamOut]:
    return _streams_out(_get(db, campaign_id))


@router.post("/{campaign_id}/fetch", response_model=list[StreamOut])
async def fetch(campaign_id: int, db: Session = Depends(get_db),
                keitaro=Depends(get_keitaro)) -> list[StreamOut]:
    c = _get(db, campaign_id)
    await fetch_campaign(db, keitaro, c)
    return _streams_out(c)

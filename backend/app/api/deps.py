from app.core.config import settings
from app.core.db import get_db  # noqa: F401 (re-export for routers)
from app.keitaro.client import KeitaroClient
from app.keitaro.fake import FakeKeitaro

# Module-level singleton so campaigns/streams survive across requests in demo mode.
_fake_keitaro: FakeKeitaro | None = None

_DEMO_OFFERS: dict[int, dict] = {
    18001: {"id": 18001, "name": "Offer Alpha — Tier1 Finance"},
    18002: {"id": 18002, "name": "Offer Beta — Crypto Leads"},
    18003: {"id": 18003, "name": "Offer Gamma — Insurance US"},
    18004: {"id": 18004, "name": "Offer Delta — Gambling EU"},
    18005: {"id": 18005, "name": "Offer Epsilon — Nutra UK"},
    18006: {"id": 18006, "name": "Offer Zeta — Binary Options"},
    18007: {"id": 18007, "name": "Offer Eta — Solar Leads"},
    18008: {"id": 18008, "name": "Offer Theta — Health Supp"},
    18009: {"id": 18009, "name": "Offer Iota — Travel Asia"},
    18010: {"id": 18010, "name": "Offer Kappa — Forex Premium"},
}


def _get_fake_keitaro() -> FakeKeitaro:
    global _fake_keitaro
    if _fake_keitaro is None:
        _fake_keitaro = FakeKeitaro(offers=_DEMO_OFFERS)
    return _fake_keitaro


def get_keitaro() -> KeitaroClient | FakeKeitaro:
    if settings.use_fake_keitaro:
        return _get_fake_keitaro()
    return KeitaroClient(settings.keitaro_base_url, settings.keitaro_api_key)

from app.core.config import settings
from app.core.db import get_db  # noqa: F401 (re-export for routers)
from app.keitaro.client import KeitaroClient


def get_keitaro() -> KeitaroClient:
    return KeitaroClient(settings.keitaro_base_url, settings.keitaro_api_key)

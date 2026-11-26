# Adrobot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Keitaro Admin API wrapper — Part 1 campaign creator (campaign + 2 streams) and Part 2 draft/publish campaign editor (add/remove/bring-back/pin offers, weight rebalance, archive, reverse-sync REM, push-conflict detection) — with a FastAPI backend and a React SPA.

**Architecture:** Layered backend (api → services → keitaro client + repositories → models). Keitaro owns published data; local Postgres owns draft state, published snapshots, and a last-seen signature for conflict detection. The weight-rebalance core is a pure function. A `FakeKeitaro` makes all service tests deterministic and offline.

**Tech Stack:** FastAPI, sync SQLAlchemy 2.0 + psycopg, Postgres (Docker Compose), Alembic, async httpx, pydantic-settings, pytest; React + TypeScript + Vite → GitHub Pages.

**Spec:** [`docs/superpowers/specs/2026-11-26-adrobot-design.md`](../specs/2026-11-26-adrobot-design.md)

---

## File structure

```
adrobot/
├── docker-compose.yml            # Postgres service
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env.example
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, routers, exception handlers
│   │   ├── core/
│   │   │   ├── config.py         # pydantic-settings
│   │   │   ├── db.py             # engine, SessionLocal, Base, get_db
│   │   │   └── errors.py         # typed exceptions
│   │   ├── models.py             # Campaign, Stream, OfferState ORM
│   │   ├── schemas.py            # pydantic request/response models
│   │   ├── keitaro/
│   │   │   ├── base.py           # KeitaroPort protocol + DTOs
│   │   │   ├── client.py         # httpx-backed client
│   │   │   └── fake.py           # FakeKeitaro (in-memory)
│   │   ├── services/
│   │   │   ├── shares.py         # PURE rebalance function
│   │   │   ├── signature.py      # stream signature hashing
│   │   │   ├── creator.py        # Part 1
│   │   │   ├── editor.py         # add/remove/bring-back/pin
│   │   │   ├── sync.py           # fetch + reverse-sync REM
│   │   │   └── publisher.py      # push/cancel + conflict
│   │   └── api/
│   │       ├── deps.py           # DI: db session, keitaro client
│   │       ├── campaigns.py
│   │       ├── streams.py
│   │       └── offers.py
│   └── tests/
│       ├── conftest.py
│       ├── test_shares.py
│       ├── test_signature.py
│       ├── test_creator.py
│       ├── test_editor.py
│       ├── test_sync.py
│       ├── test_publisher.py
│       └── test_walkthrough.py
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    ├── .env.example
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── api.ts                # typed fetch client (VITE_API_URL)
    │   ├── types.ts
    │   ├── pages/CreateCampaign.tsx
    │   ├── pages/Editor.tsx
    │   └── components/{CountrySelect,OfferPicker,StreamCard,OfferRow}.tsx
    └── .github/workflows/deploy-pages.yml   # (lives at repo root .github/)
```

**Testing DB note:** runtime uses Postgres; tests use SQLite in-memory for speed and zero setup. Models use SQLAlchemy's portable `JSON` type (maps to JSONB on Postgres, JSON on SQLite), so no schema divergence in the fields we rely on. `FakeKeitaro` removes any network dependency.

---

## Phase 0 — Backend scaffolding

### Task 0.1: Backend project skeleton + dependencies

**Files:**
- Create: `backend/requirements.txt`, `backend/.env.example`, `backend/pytest.ini`, `backend/app/__init__.py`, `backend/tests/__init__.py`

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
sqlalchemy==2.0.36
psycopg[binary]==3.2.3
alembic==1.14.0
httpx==0.28.1
pydantic==2.10.3
pydantic-settings==2.6.1
pycountry==24.6.1
pytest==8.3.4
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Create `backend/.env.example`**

```
# Backend config. Copy to backend/.env and fill in your Keitaro key.
KEITARO_API_KEY=your_api_key_here
KEITARO_BASE_URL=https://keitaro-for-tests.etolegko.com/admin_api/v1
# Runtime DB (Postgres via docker-compose). Tests ignore this and use SQLite.
DATABASE_URL=postgresql+psycopg://adrobot:adrobot@localhost:5432/adrobot
# Fallback catalog IDs if API resolution is skipped/unavailable
KEITARO_DOMAIN_ID=1813
KEITARO_GROUP_ID=10332
KEITARO_SOURCE_ID=836
# Comma-separated CORS origins (SPA)
CORS_ORIGINS=http://localhost:5173,http://localhost:4173
```

- [ ] **Step 3: Create `backend/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
testpaths = tests
```

- [ ] **Step 4: Create empty `backend/app/__init__.py` and `backend/tests/__init__.py`**

```python
# backend/app/__init__.py
```

```python
# backend/tests/__init__.py
```

- [ ] **Step 5: Create venv and install**

Run: `cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
Expected: installs without error; `pytest --version` works.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/pytest.ini backend/app/__init__.py backend/tests/__init__.py
git commit -m "chore: backend skeleton + dependencies"
```

### Task 0.2: Config

**Files:**
- Create: `backend/app/core/__init__.py`, `backend/app/core/config.py`

- [ ] **Step 1: Create `backend/app/core/__init__.py`** (empty)

- [ ] **Step 2: Create `backend/app/core/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    keitaro_api_key: str = "test-key"
    keitaro_base_url: str = "https://keitaro-for-tests.etolegko.com/admin_api/v1"
    database_url: str = "postgresql+psycopg://adrobot:adrobot@localhost:5432/adrobot"
    keitaro_domain_id: int = 1813
    keitaro_group_id: int = 10332
    keitaro_source_id: int = 836
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/__init__.py backend/app/core/config.py
git commit -m "feat: backend config via pydantic-settings"
```

### Task 0.3: DB session + Base

**Files:**
- Create: `backend/app/core/db.py`

- [ ] **Step 1: Create `backend/app/core/db.py`**

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/db.py
git commit -m "feat: SQLAlchemy engine, session, declarative Base"
```

### Task 0.4: Typed errors

**Files:**
- Create: `backend/app/core/errors.py`

- [ ] **Step 1: Create `backend/app/core/errors.py`**

```python
class AppError(Exception):
    """Base application error with an HTTP status and safe message."""
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ValidationError(AppError):
    status_code = 422


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UpstreamError(AppError):
    status_code = 502
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/errors.py
git commit -m "feat: typed application errors"
```

### Task 0.5: Docker Compose for Postgres

**Files:**
- Create: `docker-compose.yml` (repo root)

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: adrobot
      POSTGRES_PASSWORD: adrobot
      POSTGRES_DB: adrobot
    ports:
      - "5432:5432"
    volumes:
      - adrobot_pg:/var/lib/postgresql/data

volumes:
  adrobot_pg:
```

- [ ] **Step 2: Verify it starts**

Run: `docker compose up -d && docker compose ps`
Expected: `db` service is `running`/healthy.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: Postgres via docker-compose"
```

---

## Phase 1 — Weight rebalance (pure function, TDD first)

### Task 1.1: `rebalance` — even split, no pins

**Files:**
- Create: `backend/app/services/__init__.py`, `backend/app/services/shares.py`
- Test: `backend/tests/test_shares.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_shares.py
from app.services.shares import OfferShare, rebalance


def shares(result):
    return [o.share for o in result]


def test_four_active_even():
    offers = [OfferShare(i, "active", False, 0) for i in range(4)]
    assert shares(rebalance(offers)) == [25, 25, 25, 25]


def test_three_active_remainder_to_first():
    offers = [OfferShare(i, "active", False, 0) for i in range(3)]
    assert shares(rebalance(offers)) == [34, 33, 33]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . .venv/bin/activate && pytest tests/test_shares.py -v`
Expected: FAIL (`ModuleNotFoundError: app.services.shares`).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/__init__.py
```

```python
# backend/app/services/shares.py
from dataclasses import dataclass

from app.core.errors import ValidationError


@dataclass
class OfferShare:
    offer_id: int
    status: str       # "active" | "removed"
    pinned: bool
    share: int        # pinned-active: locked value; otherwise recomputed


def rebalance(offers: list[OfferShare]) -> list[OfferShare]:
    for o in offers:
        if o.status == "removed":
            o.share = 0
            o.pinned = False

    active = [o for o in offers if o.status == "active"]
    pinned = [o for o in active if o.pinned]
    free = [o for o in active if not o.pinned]

    for o in pinned:
        if not 0 <= o.share <= 100:
            raise ValidationError(f"pinned share {o.share} out of range 0..100")
    pinned_sum = sum(o.share for o in pinned)
    if pinned_sum > 100:
        raise ValidationError("pinned shares exceed 100%")

    remain = 100 - pinned_sum
    if not free:
        if active and pinned_sum != 100:
            raise ValidationError("pinned shares must total 100% when no free offers")
        return offers
    if remain <= 0:
        raise ValidationError("pinned shares leave no room for other offers")

    base = remain // len(free)
    extra = remain - base * len(free)
    for i, o in enumerate(free):
        o.share = base + (1 if i < extra else 0)
    return offers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_shares.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/shares.py backend/tests/test_shares.py
git commit -m "feat: pure weight rebalance — even split (TDD)"
```

### Task 1.2: `rebalance` — removed offers, pins, validation

**Files:**
- Modify: `backend/tests/test_shares.py`

- [ ] **Step 1: Add failing tests**

```python
# append to backend/tests/test_shares.py
import pytest

from app.core.errors import ValidationError


def test_removed_offer_zeroed_and_excluded():
    offers = [
        OfferShare(1, "active", False, 0),
        OfferShare(2, "active", False, 0),
        OfferShare(3, "removed", False, 99),
    ]
    out = rebalance(offers)
    by_id = {o.offer_id: o.share for o in out}
    assert by_id == {1: 50, 2: 50, 3: 0}


def test_pin_even_split_of_remainder():
    offers = [
        OfferShare(1, "active", True, 25),
        OfferShare(2, "active", False, 0),
        OfferShare(3, "active", False, 0),
    ]
    out = rebalance(offers)
    assert [o.share for o in out] == [25, 38, 37]


def test_pin_user_set_value():
    offers = [
        OfferShare(1, "active", True, 40),
        OfferShare(2, "active", False, 0),
        OfferShare(3, "active", False, 0),
    ]
    out = rebalance(offers)
    assert [o.share for o in out] == [40, 30, 30]


def test_pins_over_100_rejected():
    offers = [OfferShare(1, "active", True, 60), OfferShare(2, "active", True, 50)]
    with pytest.raises(ValidationError):
        rebalance(offers)


def test_pin_leaves_no_room_rejected():
    offers = [OfferShare(1, "active", True, 100), OfferShare(2, "active", False, 0)]
    with pytest.raises(ValidationError):
        rebalance(offers)


def test_all_pinned_must_total_100():
    ok = [OfferShare(1, "active", True, 60), OfferShare(2, "active", True, 40)]
    assert [o.share for o in rebalance(ok)] == [60, 40]
    bad = [OfferShare(1, "active", True, 60), OfferShare(2, "active", True, 30)]
    with pytest.raises(ValidationError):
        rebalance(bad)
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_shares.py -v`
Expected: PASS (implementation from Task 1.1 already covers these). If any fail, fix `shares.py` until green.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_shares.py
git commit -m "test: rebalance pins, removed, validation edge cases"
```

---

## Phase 2 — Keitaro client port + FakeKeitaro

### Task 2.1: Keitaro port + DTOs

**Files:**
- Create: `backend/app/keitaro/__init__.py`, `backend/app/keitaro/base.py`

- [ ] **Step 1: Create `backend/app/keitaro/__init__.py`** (empty)

- [ ] **Step 2: Create `backend/app/keitaro/base.py`**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/keitaro/__init__.py backend/app/keitaro/base.py
git commit -m "feat: Keitaro port protocol + DTOs"
```

### Task 2.2: FakeKeitaro (in-memory)

**Files:**
- Create: `backend/app/keitaro/fake.py`
- Test: `backend/tests/test_fake_keitaro.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_fake_keitaro.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fake_keitaro.py -v`
Expected: FAIL (`app.keitaro.fake` missing).

- [ ] **Step 3: Write implementation**

```python
# backend/app/keitaro/fake.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fake_keitaro.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/keitaro/fake.py backend/tests/test_fake_keitaro.py
git commit -m "feat: FakeKeitaro in-memory client (TDD)"
```

### Task 2.3: Real httpx-backed client

**Files:**
- Create: `backend/app/keitaro/client.py`

- [ ] **Step 1: Create `backend/app/keitaro/client.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/keitaro/client.py
git commit -m "feat: httpx-backed Keitaro client"
```

---

## Phase 3 — Models + migration

### Task 3.1: ORM models

**Files:**
- Create: `backend/app/models.py`

- [ ] **Step 1: Create `backend/app/models.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_campaign_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    alias: Mapped[str] = mapped_column(String(255), default="")
    geos: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    streams: Mapped[list["Stream"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan")


class Stream(Base):
    __tablename__ = "streams"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    keitaro_stream_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(16), default="offers")  # offers|opaque
    is_dirty: Mapped[bool] = mapped_column(Boolean, default=False)
    published_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    keitaro_signature: Mapped[str] = mapped_column(String(64), default="")
    campaign: Mapped["Campaign"] = relationship(back_populates="streams")
    offers: Mapped[list["OfferState"]] = relationship(
        back_populates="stream", cascade="all, delete-orphan")


class OfferState(Base):
    __tablename__ = "offer_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id"))
    keitaro_offer_id: Mapped[int] = mapped_column(Integer)
    offer_name: Mapped[str] = mapped_column(String(512), default="")
    share: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")   # active|removed
    origin: Mapped[str] = mapped_column(String(16), default="local")    # local|keitaro
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    published_share: Mapped[int] = mapped_column(Integer, default=0)
    stream: Mapped["Stream"] = relationship(back_populates="offers")
```

- [ ] **Step 2: Smoke-test model import + table creation on SQLite**

```python
# backend/tests/test_models.py
from sqlalchemy import create_engine

from app.core.db import Base
from app import models  # noqa: F401  (register tables)


def test_metadata_creates_on_sqlite():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    assert {"campaigns", "streams", "offer_states"} <= set(Base.metadata.tables)
```

- [ ] **Step 3: Run**

Run: `pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat: ORM models (campaign, stream, offer_state)"
```

### Task 3.2: Alembic init + first migration

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/` (initial migration)

- [ ] **Step 1: Initialize Alembic**

Run: `cd backend && . .venv/bin/activate && alembic init alembic`
Expected: creates `alembic.ini` + `alembic/`.

- [ ] **Step 2: Point `alembic/env.py` at our metadata + URL**

Replace the config/url and `target_metadata` sections of `backend/alembic/env.py` so it reads:

```python
# near the top, after existing imports
from app.core.config import settings
from app.core.db import Base
from app import models  # noqa: F401  (register tables)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```

- [ ] **Step 3: Ensure Postgres is up**

Run: `docker compose up -d`
Expected: `db` running.

- [ ] **Step 4: Autogenerate the initial migration**

Run: `alembic revision --autogenerate -m "initial schema"`
Expected: a file in `alembic/versions/` creating `campaigns`, `streams`, `offer_states`.

- [ ] **Step 5: Apply it**

Run: `alembic upgrade head`
Expected: `Running upgrade -> <rev>, initial schema`.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: Alembic setup + initial schema migration"
```

---

## Phase 4 — Test harness (DB + fake client fixtures)

### Task 4.1: conftest with SQLite session + FakeKeitaro

**Files:**
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create `backend/tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app import models  # noqa: F401
from app.keitaro.fake import FakeKeitaro

CATALOG = {
    18001: {"id": 18001, "name": "18001 Offer A", "country": ["CL"]},
    18002: {"id": 18002, "name": "18002 Offer B", "country": ["TH"]},
    18003: {"id": 18003, "name": "18003 Offer C", "country": ["CO"]},
    18004: {"id": 18004, "name": "18004 Offer D", "country": ["BR"]},
    18005: {"id": 18005, "name": "18005 Offer E", "country": ["PE"]},
    18006: {"id": 18006, "name": "18006 Offer F", "country": ["MX"]},
}


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def keitaro():
    return FakeKeitaro(offers=dict(CATALOG))
```

- [ ] **Step 2: Sanity-run existing suite**

Run: `pytest -q`
Expected: all prior tests PASS; fixtures import cleanly.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: conftest with SQLite session + FakeKeitaro fixtures"
```

---

## Phase 5 — Part 1: campaign creator

### Task 5.1: Stream signature helper

**Files:**
- Create: `backend/app/services/signature.py`
- Test: `backend/tests/test_signature.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_signature.py
from app.keitaro.base import KOffer, KStream
from app.services.signature import stream_signature


def test_signature_is_order_independent_and_change_sensitive():
    a = KStream(1, "s", 1, "landings", [KOffer(1, 50), KOffer(2, 50)])
    b = KStream(1, "s", 1, "landings", [KOffer(2, 50), KOffer(1, 50)])
    c = KStream(1, "s", 1, "landings", [KOffer(1, 60), KOffer(2, 40)])
    assert stream_signature(a) == stream_signature(b)
    assert stream_signature(a) != stream_signature(c)
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_signature.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/app/services/signature.py
import hashlib

from app.keitaro.base import KStream


def stream_signature(stream: KStream) -> str:
    pairs = sorted((o.offer_id, o.share) for o in stream.offers)
    raw = ";".join(f"{oid}:{share}" for oid, share in pairs)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_signature.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/signature.py backend/tests/test_signature.py
git commit -m "feat: stream signature for conflict detection (TDD)"
```

### Task 5.2: Creator service

**Files:**
- Create: `backend/app/services/creator.py`
- Test: `backend/tests/test_creator.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_creator.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_creator.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/app/services/creator.py
import pycountry

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ValidationError
from app.keitaro.base import KeitaroPort
from app import models


def _validate_geos(geos: list[str]) -> list[str]:
    if not geos:
        raise ValidationError("at least one geo is required")
    out = []
    for g in geos:
        code = g.strip().upper()
        if not pycountry.countries.get(alpha_2=code):
            raise ValidationError(f"invalid ISO country code: {g}")
        out.append(code)
    return out


async def create_campaign(db: Session, keitaro: KeitaroPort, *,
                          name: str, geos: list[str], offer_id: int) -> models.Campaign:
    geos = _validate_geos(geos)
    if await keitaro.get_offer(offer_id) is None:
        raise ValidationError(f"offer {offer_id} not found in Keitaro")

    kcamp = await keitaro.create_campaign(
        name=name, group_id=settings.keitaro_group_id,
        traffic_source_id=settings.keitaro_source_id,
        domain_id=settings.keitaro_domain_id)

    try:
        s1 = await keitaro.create_stream({
            "campaign_id": kcamp.id, "name": f"Geo {'/'.join(geos)}",
            "type": "regular", "schema": "redirect",
            "action_type": "http", "action_payload": "https://google.com",
            "filters": [{"name": "country", "mode": "accept", "payload": geos}]})
        s2 = await keitaro.create_stream({
            "campaign_id": kcamp.id, "name": "Offers",
            "type": "default", "schema": "landings",
            "offers": [{"offer_id": offer_id, "share": 100, "state": "active"}]})
    except Exception:
        await keitaro.delete_campaign(kcamp.id)
        raise

    campaign = models.Campaign(keitaro_campaign_id=kcamp.id, name=kcamp.name,
                               alias=kcamp.alias, geos=geos)
    db.add(campaign)
    db.flush()

    campaign.streams.append(models.Stream(
        keitaro_stream_id=s1.id, position=s1.position, kind="opaque"))
    offers_stream = models.Stream(
        keitaro_stream_id=s2.id, position=s2.position, kind="offers")
    offers_stream.offers.append(models.OfferState(
        keitaro_offer_id=offer_id, share=100, status="active",
        published_share=100))
    campaign.streams.append(offers_stream)
    db.commit()
    return campaign
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_creator.py -v`
Expected: PASS (all four).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/creator.py backend/tests/test_creator.py
git commit -m "feat: Part 1 campaign creator + rollback (TDD)"
```

---

## Phase 6 — Part 2: editor service

### Task 6.1: Editor helpers — apply rebalance to a stream's offers

**Files:**
- Create: `backend/app/services/editor.py`
- Test: `backend/tests/test_editor.py`

- [ ] **Step 1: Write failing tests (add + remove + rebalance + dirty)**

```python
# backend/tests/test_editor.py
import pytest

from app.services import editor
from app.services.creator import create_campaign
from app import models


async def _campaign_with_offers_stream(db, keitaro, n=1):
    camp = await create_campaign(db, keitaro, name="test_quang_e",
                                 geos=["GM"], offer_id=18001)
    stream = next(s for s in camp.streams if s.kind == "offers")
    return camp, stream


@pytest.mark.asyncio
async def test_add_offer_rebalances_and_dirties(db, keitaro):
    _, stream = await _campaign_with_offers_stream(db, keitaro)
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    shares = sorted(o.share for o in stream.offers if o.status == "active")
    assert shares == [50, 50]
    assert stream.is_dirty is True


@pytest.mark.asyncio
async def test_remove_offer_grays_and_zeros(db, keitaro):
    _, stream = await _campaign_with_offers_stream(db, keitaro)
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    editor.remove_offer(db, stream, offer_id=18002)
    removed = next(o for o in stream.offers if o.keitaro_offer_id == 18002)
    assert removed.status == "removed" and removed.origin == "local"
    assert removed.share == 0
    active = [o for o in stream.offers if o.status == "active"]
    assert active[0].share == 100


@pytest.mark.asyncio
async def test_bring_back_reactivates(db, keitaro):
    _, stream = await _campaign_with_offers_stream(db, keitaro)
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    editor.remove_offer(db, stream, offer_id=18002)
    editor.bring_back(db, stream, offer_id=18002)
    assert all(o.status == "active" for o in stream.offers)
    assert sorted(o.share for o in stream.offers) == [50, 50]


@pytest.mark.asyncio
async def test_pin_sets_value_and_dirties_only_on_value(db, keitaro):
    _, stream = await _campaign_with_offers_stream(db, keitaro)
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    editor.add_offer(db, stream, offer_id=18003, offer_name="C")
    stream.is_dirty = False
    # pin toggle without value -> not dirty
    editor.pin(db, stream, offer_id=18001, pinned=True, share=None)
    assert stream.is_dirty is False
    # pin with explicit value -> dirty
    editor.pin(db, stream, offer_id=18001, pinned=True, share=40)
    pinned = next(o for o in stream.offers if o.keitaro_offer_id == 18001)
    assert pinned.pinned and pinned.share == 40
    others = sorted(o.share for o in stream.offers if not o.pinned)
    assert others == [30, 30]
    assert stream.is_dirty is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_editor.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/app/services/editor.py
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.services.shares import OfferShare, rebalance
from app import models


def _rebalance_stream(stream: models.Stream) -> None:
    shares = [OfferShare(o.keitaro_offer_id, o.status, o.pinned, o.share)
              for o in stream.offers]
    rebalance(shares)
    by_id = {s.offer_id: s for s in shares}
    for o in stream.offers:
        s = by_id[o.keitaro_offer_id]
        o.share = s.share
        o.pinned = s.pinned


def _find(stream: models.Stream, offer_id: int) -> models.OfferState:
    for o in stream.offers:
        if o.keitaro_offer_id == offer_id:
            return o
    raise NotFoundError(f"offer {offer_id} not in stream")


def add_offer(db: Session, stream: models.Stream, *, offer_id: int, offer_name: str) -> None:
    existing = next((o for o in stream.offers if o.keitaro_offer_id == offer_id), None)
    if existing and existing.status == "active":
        raise ValidationError(f"offer {offer_id} already active in stream")
    if existing:
        existing.status = "active"
        existing.origin = "local"
    else:
        stream.offers.append(models.OfferState(
            keitaro_offer_id=offer_id, offer_name=offer_name,
            status="active", origin="local", share=0))
    _rebalance_stream(stream)
    stream.is_dirty = True
    db.commit()


def remove_offer(db: Session, stream: models.Stream, *, offer_id: int) -> None:
    o = _find(stream, offer_id)
    o.status = "removed"
    o.origin = "local"
    o.pinned = False
    _rebalance_stream(stream)
    stream.is_dirty = True
    db.commit()


def bring_back(db: Session, stream: models.Stream, *, offer_id: int) -> None:
    o = _find(stream, offer_id)
    o.status = "active"
    _rebalance_stream(stream)
    stream.is_dirty = True
    db.commit()


def pin(db: Session, stream: models.Stream, *, offer_id: int,
        pinned: bool, share: int | None) -> None:
    o = _find(stream, offer_id)
    if o.status != "active":
        raise ValidationError("can only pin an active offer")
    o.pinned = pinned
    if pinned and share is not None:
        o.share = share
        stream.is_dirty = True       # a value change is a publishable change
    _rebalance_stream(stream)
    db.commit()
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_editor.py -v`
Expected: PASS (all four).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/editor.py backend/tests/test_editor.py
git commit -m "feat: Part 2 editor — add/remove/bring-back/pin (TDD)"
```

---

## Phase 7 — Sync (fetch + reverse-sync REM)

### Task 7.1: Sync service

**Files:**
- Create: `backend/app/services/sync.py`
- Test: `backend/tests/test_sync.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_sync.py
import pytest

from app.services.creator import create_campaign
from app.services.sync import fetch_campaign
from app import models


@pytest.mark.asyncio
async def test_fetch_marks_missing_offer_as_rem(db, keitaro):
    camp = await create_campaign(db, keitaro, name="test_quang_s",
                                 geos=["GM"], offer_id=18001)
    offers_stream = next(s for s in camp.streams if s.kind == "offers")
    # add a 2nd offer and publish it directly into the fake (simulate prior push)
    from app.keitaro.base import KOffer
    await keitaro.update_stream_offers(
        offers_stream.keitaro_stream_id, [KOffer(18001, 50), KOffer(18002, 50)])
    # our local DB also knows about 18002 as active
    offers_stream.offers.append(models.OfferState(
        keitaro_offer_id=18002, status="active", share=50, published_share=50))
    db.commit()
    # admin deletes 18002 from Keitaro
    keitaro.admin_remove_offer(offers_stream.keitaro_stream_id, 18002)

    await fetch_campaign(db, keitaro, camp)
    rem = next(o for o in offers_stream.offers if o.keitaro_offer_id == 18002)
    assert rem.status == "removed" and rem.origin == "keitaro"


@pytest.mark.asyncio
async def test_fetch_preserves_opaque_streams(db, keitaro):
    camp = await create_campaign(db, keitaro, name="test_quang_s2",
                                 geos=["GM"], offer_id=18001)
    await fetch_campaign(db, keitaro, camp)
    kinds = sorted(s.kind for s in camp.streams)
    assert kinds == ["offers", "opaque"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_sync.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/app/services/sync.py
from sqlalchemy.orm import Session

from app.keitaro.base import KeitaroPort
from app.services.signature import stream_signature
from app import models


async def fetch_campaign(db: Session, keitaro: KeitaroPort,
                         campaign: models.Campaign) -> models.Campaign:
    kstreams = await keitaro.get_campaign_streams(campaign.keitaro_campaign_id)
    local_by_kid = {s.keitaro_stream_id: s for s in campaign.streams}

    for ks in kstreams:
        local = local_by_kid.get(ks.id)
        if local is None:
            local = models.Stream(
                keitaro_stream_id=ks.id, position=ks.position,
                kind="offers" if ks.schema == "landings" else "opaque")
            campaign.streams.append(local)
        local.position = ks.position

        if local.kind != "offers":
            continue

        local.keitaro_signature = stream_signature(ks)
        upstream_ids = {o.offer_id for o in ks.offers}
        known = {o.keitaro_offer_id: o for o in local.offers}

        # reverse-sync: offers we knew but are gone upstream -> REM (unless already removed)
        for oid, o in known.items():
            if o.status == "active" and oid not in upstream_ids:
                o.status = "removed"
                o.origin = "keitaro"
                o.pinned = False
                o.share = 0

    db.commit()
    return campaign
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_sync.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/sync.py backend/tests/test_sync.py
git commit -m "feat: fetch + reverse-sync REM (TDD)"
```

---

## Phase 8 — Publisher (push/cancel + conflict)

### Task 8.1: Publisher service

**Files:**
- Create: `backend/app/services/publisher.py`
- Test: `backend/tests/test_publisher.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_publisher.py
import pytest

from app.core.errors import ConflictError
from app.services import editor
from app.services.creator import create_campaign
from app.services.publisher import push_stream, cancel_stream
from app.keitaro.base import KOffer


async def _stream_with_two(db, keitaro):
    camp = await create_campaign(db, keitaro, name="test_quang_p",
                                 geos=["GM"], offer_id=18001)
    stream = next(s for s in camp.streams if s.kind == "offers")
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    return camp, stream


@pytest.mark.asyncio
async def test_push_sends_active_offers_and_clears_dirty(db, keitaro):
    _, stream = await _stream_with_two(db, keitaro)
    await push_stream(db, keitaro, stream)
    ks = (await keitaro.get_campaign_streams(stream.campaign.keitaro_campaign_id))
    pushed = next(s for s in ks if s.id == stream.keitaro_stream_id)
    assert sorted(o.offer_id for o in pushed.offers) == [18001, 18002]
    assert stream.is_dirty is False
    assert all(o.published_share == o.share for o in stream.offers if o.status == "active")


@pytest.mark.asyncio
async def test_push_conflict_when_keitaro_changed(db, keitaro):
    _, stream = await _stream_with_two(db, keitaro)
    await push_stream(db, keitaro, stream)
    # someone edits Keitaro directly -> signature diverges
    await keitaro.update_stream_offers(stream.keitaro_stream_id, [KOffer(18001, 100)])
    editor.add_offer(db, stream, offer_id=18003, offer_name="C")
    with pytest.raises(ConflictError):
        await push_stream(db, keitaro, stream)


@pytest.mark.asyncio
async def test_cancel_restores_published_snapshot(db, keitaro):
    _, stream = await _stream_with_two(db, keitaro)
    await push_stream(db, keitaro, stream)       # snapshot = {18001,18002}
    editor.add_offer(db, stream, offer_id=18003, offer_name="C")
    cancel_stream(db, stream)
    ids = sorted(o.keitaro_offer_id for o in stream.offers if o.status == "active")
    assert ids == [18001, 18002]
    assert stream.is_dirty is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_publisher.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/app/services/publisher.py
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ValidationError
from app.keitaro.base import KeitaroPort, KOffer
from app.services.signature import stream_signature
from app import models


def _active(stream: models.Stream) -> list[models.OfferState]:
    return [o for o in stream.offers if o.status == "active"]


def _snapshot(stream: models.Stream) -> list[dict]:
    return [{"offer_id": o.keitaro_offer_id, "offer_name": o.offer_name,
             "share": o.share, "status": o.status, "origin": o.origin,
             "pinned": o.pinned} for o in stream.offers]


async def push_stream(db: Session, keitaro: KeitaroPort, stream: models.Stream) -> None:
    active = _active(stream)
    total = sum(o.share for o in active)
    if active and total != 100:
        raise ValidationError(f"active shares must total 100, got {total}")

    # conflict check: compare stored signature against Keitaro's current state
    if stream.keitaro_signature:
        kstreams = await keitaro.get_campaign_streams(stream.campaign.keitaro_campaign_id)
        current = next((s for s in kstreams if s.id == stream.keitaro_stream_id), None)
        if current is not None and stream_signature(current) != stream.keitaro_signature:
            raise ConflictError("Keitaro changed underneath; re-fetch before pushing")

    koffers = [KOffer(o.keitaro_offer_id, o.share, "active") for o in active]
    updated = await keitaro.update_stream_offers(stream.keitaro_stream_id, koffers)

    for o in stream.offers:
        o.published_share = o.share if o.status == "active" else 0
    stream.published_snapshot = _snapshot(stream)
    stream.keitaro_signature = stream_signature(updated)
    stream.is_dirty = False
    db.commit()


def cancel_stream(db: Session, stream: models.Stream) -> None:
    snap = {s["offer_id"]: s for s in (stream.published_snapshot or [])}
    # drop offers that were never published; restore the rest
    for o in list(stream.offers):
        if o.keitaro_offer_id not in snap:
            stream.offers.remove(o)
            db.delete(o)
        else:
            s = snap[o.keitaro_offer_id]
            o.share = s["share"]
            o.status = s["status"]
            o.origin = s["origin"]
            o.pinned = s["pinned"]
            o.published_share = s["share"] if s["status"] == "active" else 0
    stream.is_dirty = False
    db.commit()
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_publisher.py -v`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/publisher.py backend/tests/test_publisher.py
git commit -m "feat: publisher push/cancel + conflict detection (TDD)"
```

---

## Phase 9 — End-to-end walkthrough test

### Task 9.1: Full video-scenario test

**Files:**
- Create: `backend/tests/test_walkthrough.py`

- [ ] **Step 1: Write the test (mirrors the spec's acceptance scenario)**

```python
# backend/tests/test_walkthrough.py
import pytest

from app.services import editor
from app.services.creator import create_campaign
from app.services.publisher import push_stream, cancel_stream
from app.services.sync import fetch_campaign


def active_shares(stream):
    return sorted(o.share for o in stream.offers if o.status == "active")


@pytest.mark.asyncio
async def test_full_walkthrough(db, keitaro):
    # 1. create campaign -> 2 streams, offer @100
    camp = await create_campaign(db, keitaro, name="test_quang_w",
                                 geos=["GM", "FR"], offer_id=18001)
    stream = next(s for s in camp.streams if s.kind == "offers")
    assert active_shares(stream) == [100]

    # 2-3. grow to 3 then 4 offers
    editor.add_offer(db, stream, offer_id=18002, offer_name="B")
    editor.add_offer(db, stream, offer_id=18003, offer_name="C")
    assert active_shares(stream) == [33, 33, 34]
    editor.add_offer(db, stream, offer_id=18004, offer_name="D")
    assert active_shares(stream) == [25, 25, 25, 25]
    assert stream.is_dirty is True

    # 4. push -> not dirty, all four live
    await push_stream(db, keitaro, stream)
    assert stream.is_dirty is False

    # 5. add then cancel -> the added-but-unpublished offer vanishes
    editor.add_offer(db, stream, offer_id=18005, offer_name="E")
    assert active_shares(stream) == [20, 20, 20, 20, 20]
    cancel_stream(db, stream)
    assert active_shares(stream) == [25, 25, 25, 25]
    assert 18005 not in [o.keitaro_offer_id for o in stream.offers]

    # 6. remove -> gray/0, push -> gone upstream but archived locally
    editor.remove_offer(db, stream, offer_id=18004)
    await push_stream(db, keitaro, stream)
    archived = next(o for o in stream.offers if o.keitaro_offer_id == 18004)
    assert archived.status == "removed" and archived.share == 0

    # 7. bring back -> active -> push
    editor.bring_back(db, stream, offer_id=18004)
    await push_stream(db, keitaro, stream)
    assert 18004 in [o.keitaro_offer_id for o in stream.offers if o.status == "active"]

    # 8. admin deletes an offer in Keitaro -> fetch -> REM
    keitaro.admin_remove_offer(stream.keitaro_stream_id, 18003)
    await fetch_campaign(db, keitaro, camp)
    rem = next(o for o in stream.offers if o.keitaro_offer_id == 18003)
    assert rem.status == "removed" and rem.origin == "keitaro"

    # 9. pin at 25 -> others fill to 100
    editor.pin(db, stream, offer_id=18001, pinned=True, share=25)
    pinned = next(o for o in stream.offers if o.keitaro_offer_id == 18001)
    assert pinned.share == 25
    assert sum(o.share for o in stream.offers if o.status == "active") == 100
```

- [ ] **Step 2: Run**

Run: `pytest tests/test_walkthrough.py -v`
Expected: PASS.

- [ ] **Step 3: Full suite green**

Run: `pytest -q`
Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_walkthrough.py
git commit -m "test: full video-scenario walkthrough (TDD)"
```

---

## Phase 10 — API layer

### Task 10.1: Schemas

**Files:**
- Create: `backend/app/schemas.py`

- [ ] **Step 1: Create `backend/app/schemas.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: pydantic request/response schemas"
```

### Task 10.2: DI deps + FastAPI app + exception handlers

**Files:**
- Create: `backend/app/api/__init__.py`, `backend/app/api/deps.py`, `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/api/__init__.py`** (empty)

- [ ] **Step 2: Create `backend/app/api/deps.py`**

```python
from app.core.config import settings
from app.core.db import get_db  # noqa: F401 (re-export for routers)
from app.keitaro.client import KeitaroClient


def get_keitaro() -> KeitaroClient:
    return KeitaroClient(settings.keitaro_base_url, settings.keitaro_api_key)
```

- [ ] **Step 3: Create `backend/app/main.py`**

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import AppError
from app.api import campaigns, streams, offers

app = FastAPI(title="Adrobot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
                        content={"error": type(exc).__name__, "detail": exc.detail})


app.include_router(campaigns.router)
app.include_router(streams.router)
app.include_router(offers.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/__init__.py backend/app/api/deps.py backend/app/main.py
git commit -m "feat: FastAPI app, CORS, error handlers, DI"
```

### Task 10.3: Offers + campaigns routers

**Files:**
- Create: `backend/app/api/offers.py`, `backend/app/api/campaigns.py`

- [ ] **Step 1: Create `backend/app/api/offers.py`**

```python
from fastapi import APIRouter, Depends

from app.api.deps import get_keitaro

router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("")
async def search_offers(q: str = "", keitaro=Depends(get_keitaro)) -> list[dict]:
    offers = await keitaro.list_offers()
    if q:
        ql = q.lower()
        offers = [o for o in offers
                  if ql in str(o.get("id")) or ql in o.get("name", "").lower()]
    return offers[:50]
```

- [ ] **Step 2: Create `backend/app/api/campaigns.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_keitaro
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
    return [StreamOut(
        id=s.id, keitaro_stream_id=s.keitaro_stream_id, position=s.position,
        kind=s.kind, is_dirty=s.is_dirty,
        offers=[{"keitaro_offer_id": o.keitaro_offer_id, "offer_name": o.offer_name,
                 "share": o.share, "status": o.status, "origin": o.origin,
                 "pinned": o.pinned} for o in s.offers]) for s in c.streams]


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
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/offers.py backend/app/api/campaigns.py
git commit -m "feat: offers + campaigns routers"
```

### Task 10.4: Streams router (editor + publish)

**Files:**
- Create: `backend/app/api/streams.py`

- [ ] **Step 1: Create `backend/app/api/streams.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_keitaro
from app.core.errors import NotFoundError, ValidationError
from app.schemas import AddOfferIn, PinIn, StreamOut
from app.services import editor
from app.services.publisher import cancel_stream, push_stream
from app import models

router = APIRouter(prefix="/api/streams", tags=["streams"])


def _get(db: Session, stream_id: int) -> models.Stream:
    s = db.get(models.Stream, stream_id)
    if s is None:
        raise NotFoundError(f"stream {stream_id} not found")
    if s.kind != "offers":
        raise ValidationError("stream has no editable offers")
    return s


def _out(s: models.Stream) -> StreamOut:
    return StreamOut(
        id=s.id, keitaro_stream_id=s.keitaro_stream_id, position=s.position,
        kind=s.kind, is_dirty=s.is_dirty,
        offers=[{"keitaro_offer_id": o.keitaro_offer_id, "offer_name": o.offer_name,
                 "share": o.share, "status": o.status, "origin": o.origin,
                 "pinned": o.pinned} for o in s.offers])


@router.post("/{stream_id}/offers", response_model=StreamOut)
async def add(stream_id: int, body: AddOfferIn, db: Session = Depends(get_db),
              keitaro=Depends(get_keitaro)) -> StreamOut:
    s = _get(db, stream_id)
    offer = await keitaro.get_offer(body.offer_id)
    if offer is None:
        raise ValidationError(f"offer {body.offer_id} not found")
    editor.add_offer(db, s, offer_id=body.offer_id, offer_name=offer.get("name", ""))
    return _out(s)


@router.delete("/{stream_id}/offers/{offer_id}", response_model=StreamOut)
def remove(stream_id: int, offer_id: int, db: Session = Depends(get_db)) -> StreamOut:
    s = _get(db, stream_id)
    editor.remove_offer(db, s, offer_id=offer_id)
    return _out(s)


@router.post("/{stream_id}/offers/{offer_id}/bring-back", response_model=StreamOut)
def bring_back(stream_id: int, offer_id: int, db: Session = Depends(get_db)) -> StreamOut:
    s = _get(db, stream_id)
    editor.bring_back(db, s, offer_id=offer_id)
    return _out(s)


@router.post("/{stream_id}/offers/{offer_id}/pin", response_model=StreamOut)
def pin(stream_id: int, offer_id: int, body: PinIn,
        db: Session = Depends(get_db)) -> StreamOut:
    s = _get(db, stream_id)
    editor.pin(db, s, offer_id=offer_id, pinned=body.pinned, share=body.share)
    return _out(s)


@router.post("/{stream_id}/push", response_model=StreamOut)
async def push(stream_id: int, db: Session = Depends(get_db),
               keitaro=Depends(get_keitaro)) -> StreamOut:
    s = _get(db, stream_id)
    await push_stream(db, keitaro, s)
    return _out(s)


@router.post("/{stream_id}/cancel", response_model=StreamOut)
def cancel(stream_id: int, db: Session = Depends(get_db)) -> StreamOut:
    s = _get(db, stream_id)
    cancel_stream(db, s)
    return _out(s)
```

- [ ] **Step 2: Add an API smoke test with FastAPI TestClient**

```python
# backend/tests/test_api.py
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.core.db import Base
from app.main import app
from app.keitaro.fake import FakeKeitaro
from app import models  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.conftest import CATALOG


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    fake = FakeKeitaro(offers=dict(CATALOG))

    def _db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[deps.get_db] = _db
    app.dependency_overrides[deps.get_keitaro] = lambda: fake
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_then_add_and_push(client):
    r = client.post("/api/campaigns",
                    json={"name": "test_quang_api", "geos": ["GM"], "offer_id": 18001})
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    streams = client.get(f"/api/campaigns/{cid}/streams").json()
    offers_stream = next(s for s in streams if s["kind"] == "offers")
    sid = offers_stream["id"]
    r = client.post(f"/api/streams/{sid}/offers", json={"offer_id": 18002})
    assert r.status_code == 200
    assert sorted(o["share"] for o in r.json()["offers"]) == [50, 50]
    r = client.post(f"/api/streams/{sid}/push")
    assert r.status_code == 200
    assert r.json()["is_dirty"] is False
```

- [ ] **Step 3: Run**

Run: `pytest tests/test_api.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/streams.py backend/tests/test_api.py
git commit -m "feat: streams router + API smoke test"
```

### Task 10.5: Manual live smoke (optional, needs VPN + key)

- [ ] **Step 1: Run the server**

Run: `cd backend && . .venv/bin/activate && cp .env.example .env` then edit `.env` with your real key, then `uvicorn app.main:app --reload`.

- [ ] **Step 2: Create a campaign against the real stand**

Run: `curl -X POST localhost:8000/api/campaigns -H 'Content-Type: application/json' -d '{"name":"test_quang_live","geos":["GM"],"offer_id":18001}'`
Expected: 200 with campaign JSON. Verify in the Keitaro admin, then optionally delete.

- [ ] **Step 3: No commit (manual verification only).**

---

## Phase 11 — Frontend scaffolding

### Task 11.1: Vite React-TS app + API client + types

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/.env.example`, `frontend/src/{main.tsx,types.ts,api.ts,App.tsx}`

- [ ] **Step 1: Scaffold**

Run: `cd frontend && npm create vite@latest . -- --template react-ts && npm install && npm install @tanstack/react-query i18n-iso-countries`
Expected: Vite app created; deps installed.

- [ ] **Step 2: Create `frontend/.env.example`**

```
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 3: Set base path for GitHub Pages in `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base must match the repo name for GitHub Pages project sites
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE ?? "/adrobot/",
});
```

- [ ] **Step 4: Create `frontend/src/types.ts`**

```ts
export type Offer = {
  keitaro_offer_id: number;
  offer_name: string;
  share: number;
  status: "active" | "removed";
  origin: "local" | "keitaro";
  pinned: boolean;
};

export type Stream = {
  id: number;
  keitaro_stream_id: number;
  position: number;
  kind: "offers" | "opaque";
  is_dirty: boolean;
  offers: Offer[];
};

export type Campaign = {
  id: number;
  keitaro_campaign_id: number;
  name: string;
  alias: string;
  geos: string[];
};
```

- [ ] **Step 5: Create `frontend/src/api.ts`**

```ts
import type { Campaign, Stream } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "request failed");
  }
  return res.json() as Promise<T>;
}

export const api = {
  listCampaigns: () => req<Campaign[]>("/api/campaigns"),
  createCampaign: (name: string, geos: string[], offer_id: number) =>
    req<Campaign>("/api/campaigns", {
      method: "POST",
      body: JSON.stringify({ name, geos, offer_id }),
    }),
  getStreams: (id: number) => req<Stream[]>(`/api/campaigns/${id}/streams`),
  fetchStreams: (id: number) =>
    req<Stream[]>(`/api/campaigns/${id}/fetch`, { method: "POST" }),
  searchOffers: (q: string) =>
    req<{ id: number; name: string }[]>(`/api/offers?q=${encodeURIComponent(q)}`),
  addOffer: (sid: number, offer_id: number) =>
    req<Stream>(`/api/streams/${sid}/offers`, {
      method: "POST",
      body: JSON.stringify({ offer_id }),
    }),
  removeOffer: (sid: number, oid: number) =>
    req<Stream>(`/api/streams/${sid}/offers/${oid}`, { method: "DELETE" }),
  bringBack: (sid: number, oid: number) =>
    req<Stream>(`/api/streams/${sid}/offers/${oid}/bring-back`, { method: "POST" }),
  pin: (sid: number, oid: number, pinned: boolean, share: number | null) =>
    req<Stream>(`/api/streams/${sid}/offers/${oid}/pin`, {
      method: "POST",
      body: JSON.stringify({ pinned, share }),
    }),
  push: (sid: number) => req<Stream>(`/api/streams/${sid}/push`, { method: "POST" }),
  cancel: (sid: number) => req<Stream>(`/api/streams/${sid}/cancel`, { method: "POST" }),
};
```

- [ ] **Step 6: Verify build**

Run: `npm run build`
Expected: type-checks and builds to `dist/`.

- [ ] **Step 7: Commit**

```bash
git add frontend/ -- ':!frontend/node_modules'
git commit -m "feat: frontend scaffold, typed API client, domain types"
```

### Task 11.2: App shell with two views

**Files:**
- Modify: `frontend/src/App.tsx`, `frontend/src/main.tsx`

- [ ] **Step 1: Create `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";

const qc = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
```

- [ ] **Step 2: Create `frontend/src/App.tsx`** (simple tab switch)

```tsx
import { useState } from "react";
import CreateCampaign from "./pages/CreateCampaign";
import Editor from "./pages/Editor";

export default function App() {
  const [tab, setTab] = useState<"create" | "editor">("create");
  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h1>Adrobot</h1>
      <nav style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button onClick={() => setTab("create")} disabled={tab === "create"}>
          Create
        </button>
        <button onClick={() => setTab("editor")} disabled={tab === "editor"}>
          Editor
        </button>
      </nav>
      {tab === "create" ? <CreateCampaign /> : <Editor />}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx frontend/src/main.tsx
git commit -m "feat: app shell with create/editor tabs"
```

---

## Phase 12 — Frontend views

### Task 12.1: Country multi-select + Create view

**Files:**
- Create: `frontend/src/components/CountrySelect.tsx`, `frontend/src/components/OfferPicker.tsx`, `frontend/src/pages/CreateCampaign.tsx`

- [ ] **Step 1: Create `frontend/src/components/CountrySelect.tsx`**

```tsx
import countries from "i18n-iso-countries";
import en from "i18n-iso-countries/langs/en.json";

countries.registerLocale(en);
const ALL = Object.entries(countries.getNames("en")) as [string, string][];

export default function CountrySelect({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  return (
    <select
      multiple
      value={value}
      onChange={(e) =>
        onChange(Array.from(e.target.selectedOptions, (o) => o.value))
      }
      style={{ minWidth: 220, minHeight: 140 }}
    >
      {ALL.map(([code, name]) => (
        <option key={code} value={code}>
          {code} — {name}
        </option>
      ))}
    </select>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/OfferPicker.tsx`**

```tsx
import { useState } from "react";
import { api } from "../api";

export default function OfferPicker({
  onPick,
}: {
  onPick: (offerId: number) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<{ id: number; name: string }[]>([]);

  async function search() {
    setResults(await api.searchOffers(q));
  }

  return (
    <div>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="offer id or name"
      />
      <button type="button" onClick={search}>
        Search
      </button>
      <ul>
        {results.map((o) => (
          <li key={o.id}>
            {o.id} — {o.name}{" "}
            <button type="button" onClick={() => onPick(o.id)}>
              pick
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/pages/CreateCampaign.tsx`**

```tsx
import { useState } from "react";
import CountrySelect from "../components/CountrySelect";
import OfferPicker from "../components/OfferPicker";
import { api } from "../api";

export default function CreateCampaign() {
  const [name, setName] = useState("test_quang_");
  const [geos, setGeos] = useState<string[]>([]);
  const [offerId, setOfferId] = useState<number | null>(null);
  const [msg, setMsg] = useState("");

  async function submit() {
    try {
      const c = await api.createCampaign(name, geos, offerId!);
      setMsg(`Created campaign #${c.keitaro_campaign_id} (${c.name})`);
    } catch (e) {
      setMsg(`Error: ${(e as Error).message}`);
    }
  }

  return (
    <div>
      <h2>Create campaign</h2>
      <div>
        <label>
          Name <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
      </div>
      <div>
        Countries:
        <CountrySelect value={geos} onChange={setGeos} />
      </div>
      <div>
        Offer: {offerId ?? "none"}
        <OfferPicker onPick={setOfferId} />
      </div>
      <button onClick={submit} disabled={!geos.length || !offerId}>
        Create
      </button>
      <p>{msg}</p>
    </div>
  );
}
```

- [ ] **Step 4: Verify build**

Run: `npm run build`
Expected: builds clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CountrySelect.tsx frontend/src/components/OfferPicker.tsx frontend/src/pages/CreateCampaign.tsx
git commit -m "feat: create-campaign view (country multi-select + offer picker)"
```

### Task 12.2: Editor view — stream cards, offer rows, pin editing

**Files:**
- Create: `frontend/src/components/OfferRow.tsx`, `frontend/src/components/StreamCard.tsx`, `frontend/src/pages/Editor.tsx`

- [ ] **Step 1: Create `frontend/src/components/OfferRow.tsx`**

```tsx
import type { Offer } from "../types";

export default function OfferRow({
  offer,
  onRemove,
  onBringBack,
  onPin,
}: {
  offer: Offer;
  onRemove: () => void;
  onBringBack: () => void;
  onPin: (pinned: boolean, share: number | null) => void;
}) {
  const removed = offer.status === "removed";
  return (
    <tr style={{ color: removed ? "#999" : "inherit" }}>
      <td>{offer.keitaro_offer_id}</td>
      <td>{offer.offer_name}</td>
      <td>
        {offer.pinned ? (
          <input
            type="number"
            value={offer.share}
            min={0}
            max={100}
            style={{ width: 60 }}
            onChange={(e) => onPin(true, Number(e.target.value))}
          />
        ) : (
          `${offer.share}%`
        )}
      </td>
      <td>
        {removed && offer.origin === "keitaro" && <span>REM </span>}
        {removed ? (
          <button onClick={onBringBack}>Bring back</button>
        ) : (
          <>
            <button onClick={() => onPin(!offer.pinned, offer.pinned ? null : offer.share)}>
              {offer.pinned ? "📌 Unpin" : "Pin"}
            </button>
            <button onClick={onRemove}>Remove</button>
          </>
        )}
      </td>
    </tr>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/StreamCard.tsx`**

```tsx
import { useState } from "react";
import type { Stream } from "../types";
import { api } from "../api";
import OfferRow from "./OfferRow";
import OfferPicker from "./OfferPicker";

export default function StreamCard({
  stream,
  onChange,
}: {
  stream: Stream;
  onChange: (s: Stream) => void;
}) {
  const [err, setErr] = useState("");

  async function run(p: Promise<Stream>) {
    try {
      onChange(await p);
      setErr("");
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  if (stream.kind === "opaque") {
    return (
      <div style={{ border: "1px solid #ccc", padding: 12, margin: "8px 0" }}>
        <strong>Stream #{stream.keitaro_stream_id}</strong> (redirect — not editable)
      </div>
    );
  }

  const total = stream.offers
    .filter((o) => o.status === "active")
    .reduce((a, o) => a + o.share, 0);

  return (
    <div
      style={{
        border: "1px solid #ccc",
        padding: 12,
        margin: "8px 0",
        background: stream.is_dirty ? "#fff8d0" : "white",
      }}
    >
      <strong>Stream #{stream.keitaro_stream_id}</strong>{" "}
      {stream.is_dirty && <em>(unpublished)</em>}
      <table>
        <tbody>
          {stream.offers.map((o) => (
            <OfferRow
              key={o.keitaro_offer_id}
              offer={o}
              onRemove={() => run(api.removeOffer(stream.id, o.keitaro_offer_id))}
              onBringBack={() => run(api.bringBack(stream.id, o.keitaro_offer_id))}
              onPin={(pinned, share) => run(api.pin(stream.id, o.keitaro_offer_id, pinned, share))}
            />
          ))}
        </tbody>
      </table>
      <div>Total: {total}%</div>
      <OfferPicker onPick={(oid) => run(api.addOffer(stream.id, oid))} />
      <div style={{ marginTop: 8 }}>
        <button onClick={() => run(api.push(stream.id))}>Push to Keitaro</button>
        <button onClick={() => run(api.cancel(stream.id))}>Cancel</button>
      </div>
      {err && <p style={{ color: "crimson" }}>{err}</p>}
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/pages/Editor.tsx`**

```tsx
import { useEffect, useState } from "react";
import type { Campaign, Stream } from "../types";
import { api } from "../api";
import StreamCard from "../components/StreamCard";

export default function Editor() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [streams, setStreams] = useState<Stream[]>([]);

  useEffect(() => {
    api.listCampaigns().then(setCampaigns);
  }, []);

  async function load(id: number) {
    setSelected(id);
    setStreams(await api.getStreams(id));
  }

  function updateStream(s: Stream) {
    setStreams((prev) => prev.map((x) => (x.id === s.id ? s : x)));
  }

  return (
    <div>
      <h2>Editor</h2>
      <select
        value={selected ?? ""}
        onChange={(e) => load(Number(e.target.value))}
      >
        <option value="" disabled>
          pick a campaign
        </option>
        {campaigns.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} (#{c.keitaro_campaign_id})
          </option>
        ))}
      </select>
      {selected && (
        <button onClick={() => api.fetchStreams(selected).then(setStreams)}>
          Fetch Streams
        </button>
      )}
      {streams.map((s) => (
        <StreamCard key={s.id} stream={s} onChange={updateStream} />
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Verify build + run dev against local backend**

Run: `npm run build` then `npm run dev` (with backend running) and click through create → editor → add/remove/pin/push.
Expected: builds clean; buttons work; yellow on dirty; gray + REM on removed; totals correct.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/OfferRow.tsx frontend/src/components/StreamCard.tsx frontend/src/pages/Editor.tsx
git commit -m "feat: editor view — stream cards, offer rows, pin editing"
```

---

## Phase 13 — Deployment & docs

### Task 13.1: GitHub Pages workflow

**Files:**
- Create: `.github/workflows/deploy-pages.yml` (repo root)

- [ ] **Step 1: Create `.github/workflows/deploy-pages.yml`**

```yaml
name: Deploy frontend to Pages
on:
  push:
    branches: [main]
    paths: ["frontend/**", ".github/workflows/deploy-pages.yml"]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm run build
        env:
          VITE_BASE: /adrobot/
          VITE_API_URL: http://localhost:8000
      - uses: actions/upload-pages-artifact@v3
        with:
          path: frontend/dist
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy-pages.yml
git commit -m "ci: deploy frontend to GitHub Pages"
```

### Task 13.2: Finalize `.env.example` + README

**Files:**
- Modify: `.env.example` (repo root), `README.md`

- [ ] **Step 1: Update repo-root `.env.example` to point at backend config**

```
# This project keeps its runtime config in backend/.env (see backend/.env.example).
# Quick reference:
#   KEITARO_API_KEY=...        # your key from the Keitaro admin
#   KEITARO_BASE_URL=https://keitaro-for-tests.etolegko.com/admin_api/v1
#   DATABASE_URL=postgresql+psycopg://adrobot:adrobot@localhost:5432/adrobot
```

- [ ] **Step 2: Rewrite `README.md` "Run" section**

````markdown
## Run

### 1. Database (Postgres via Docker)
```bash
docker compose up -d
```

### 2. Backend
```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # paste your Keitaro Api-Key
alembic upgrade head            # run migrations
uvicorn app.main:app --reload   # http://localhost:8000
```

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_URL=http://localhost:8000
npm run dev                     # http://localhost:5173
```

### Tests
```bash
cd backend && . .venv/bin/activate && pytest
```

## Part 1 / Part 2
- **Create** tab: name + countries + offer → campaign with 2 streams (geo→Google, offer).
- **Editor** tab: pick a campaign → Fetch Streams → add/remove/pin offers,
  Push/Cancel. Yellow = unpublished; gray = removed (REM badge = deleted in Keitaro).
````

- [ ] **Step 3: Commit**

```bash
git add README.md .env.example
git commit -m "docs: run instructions (docker, migrations, backend, frontend, tests)"
```

---

## Phase 14 — Final verification

### Task 14.1: Full green + manual acceptance

- [ ] **Step 1: Backend suite**

Run: `cd backend && . .venv/bin/activate && pytest -q`
Expected: all PASS.

- [ ] **Step 2: Frontend build**

Run: `cd frontend && npm run build`
Expected: clean build.

- [ ] **Step 3: Manual acceptance against the live stand** (VPN + real key)

Walk the spec's §10 scenario in the UI: create → 3 offers 34/33/33 → add 4th 25×4 → push → add+cancel → remove+push → bring back+push → delete-in-Keitaro+fetch→REM → pin 25%. Confirm numbers/colors.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final verification pass"
```

---

## Notes for the implementer

- **Commit after every passing test.** The plan already encodes this.
- **Pure logic first.** `shares.rebalance` is the heart — if its tests are green, the hard part is done.
- **Don't hard-code the campaign's offer on the campaign row.** Offers live in `offer_states`.
- **`traffic_source_id`, not `source_id`** — verified gotcha (see `docs/api-reference.md`).
- **Push replaces the whole offer list** on the Keitaro stream; only `active` offers are sent.
- If the live stand's offer payload differs from `FakeKeitaro`'s shape, adjust `keitaro/client.py` mapping only — services and tests stay unchanged.

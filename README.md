# Adrobot — Keitaro API wrapper

A wrapper around the [Keitaro](https://keitaro.io/) Admin API (ad-tracker / link
constructor), built for the Adrobot test task. Two parts:

1. **Campaign creator** — given `name`, `geo_code`, `offer_id`, create a campaign
   with two streams (geo → Google, and the chosen offer), using a configured
   domain / group / source.
2. **Campaign editor** — add/remove offers in an existing campaign with weight
   recalculation, draft/publish (push/cancel), archive, bring-back,
   reverse-sync (REM), and pinned weights.

> Target stack: **FastAPI + SQLAlchemy + Alembic**. Frontend TBD.

## Status

Implemented. Backend: FastAPI + SQLAlchemy + Alembic, 29 service/API tests all green.
Frontend: React + TypeScript SPA (Vite), deployed to GitHub Pages.

## Docs

| File | What |
|------|------|
| [`docs/task-ru.md`](./docs/task-ru.md) | Original task (RU) |
| [`docs/api-reference.md`](./docs/api-reference.md) | **Verified** test-stand API reference |
| [`docs/test-stand-ru.md`](./docs/test-stand-ru.md) | Test-stand (emulator) access notes |
| [`docs/admin-api.openapi.json`](./docs/admin-api.openapi.json) | Keitaro Admin API OpenAPI spec |

The spec and implementation plan will be added under
[`docs/superpowers/`](./docs/superpowers) during brainstorming.

## Run

### 1. Database (Postgres via Docker)

```bash
docker compose up -d
```

> If local port 5432 is taken, set `PG_PORT` in `docker-compose.yml` and update
> `DATABASE_URL` in `backend/.env` to match.

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

## How AI agents were used

This project was developed with Claude Code using a spec-driven workflow
(brainstorming → spec → plan → TDD). The resulting spec and implementation plan
are tracked under [`docs/superpowers/`](./docs/superpowers); the agent's project
instructions are in [`CLAUDE.md`](./CLAUDE.md).

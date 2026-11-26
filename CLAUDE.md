# Adrobot — project instructions for Claude Code

Wrapper around the Keitaro Admin API. Two parts: Part 1 campaign creator, Part 2
draft/publish campaign editor. Authoritative requirements: [`docs/task-ru.md`](./docs/task-ru.md)
+ the video. Approved design: [`docs/superpowers/specs/2026-11-26-adrobot-design.md`](./docs/superpowers/specs/2026-11-26-adrobot-design.md).
Implementation plan: [`docs/superpowers/plans/2026-11-26-adrobot-implementation.md`](./docs/superpowers/plans/2026-11-26-adrobot-implementation.md).

## Stack (decided)
- **Backend:** FastAPI, **sync** SQLAlchemy 2.0 + `psycopg`, Alembic (real
  migrations, not `create_all`), async `httpx` for the Keitaro client,
  pydantic-settings.
- **Database:** Postgres via **Docker Compose** at runtime. Tests use SQLite
  in-memory (portable `JSON` columns) + `FakeKeitaro` — no live-stand dependency.
- **Frontend:** React + TypeScript (Vite) SPA, deployed to **GitHub Pages**.
  Backend runs locally; the SPA's API base URL is `VITE_API_URL`
  (default `http://localhost:8000`). CORS allows the Pages origin + localhost.
- **Tests:** pytest (TDD).

## Hard-won constraints (from the real test stand — see `docs/api-reference.md`)
- Base URL `https://keitaro-for-tests.etolegko.com/admin_api/v1`, header `Api-Key`.
- Fixed catalog IDs: domain `1813`, group `10332`, source `836`, offers from `18001`.
  Resolve via API when possible; config fallback is acceptable.
- Campaign create uses **`traffic_source_id`** (NOT `source_id` — verified: `source_id`
  is silently ignored and the source stays null).
- **The stand has NO archive** — `DELETE` is hard-delete. So `removed` state must
  live in the **local DB**, never upstream.
- **Push = `PUT /streams/{id}`** with `offers` **replacing the whole list**
  (send only `active` offers).

## Core domain model
- **Offer status:** `active | removed`, plus `origin: local | keitaro`.
  A `removed` offer with `origin="keitaro"` is the **REM** case (deleted upstream,
  detected on fetch) and gets a REM badge. Both origins are gray, share 0, and
  support **Bring back**.
- **Pinned = user-controlled share.** A pinned offer's % is set by the user and
  held fixed; unpinned active offers evenly split the remainder.
  - Pin/unpin **toggle** → NOT dirty. **Editing a pinned share value** → dirty.
- **Dirty** stream = unpublished changes (UI shows yellow).
- **Conflict detection:** on Push, compare a stored signature (hash of the last-seen
  Keitaro offer set) against Keitaro's current state; mismatch → **409**, re-fetch.

## The two hardest requirements (don't skip — they separate pass/fail)
1. **Reverse-sync REM** — offer deleted directly in Keitaro → on fetch, mark it
   `removed/origin=keitaro` (gray) locally, do NOT hard-delete; keep "Bring back".
2. **Pinned weights** — pinned offer's share fixed; others rebalance to fill 100%.

## Weight rebalance (pure function, test first)
- Active offers sum to 100. Removed offers = 0.
- Pinned active offers keep their user-set share.
- `remain = 100 − Σ(pinned)`, split evenly among unpinned-active; remainder → first.
- Reject (422) if Σ(pinned) > 100, a pinned share is outside 0..100, or pins leave
  no room for existing unpinned-active offers.
- Examples: 4→25/25/25/25 · 3→34/33/33 · pin 1@25%→25/38/37 · pin 1@40%→40/30/30.

## Geo (Part 1)
- **Multi-select** countries; each validated as ISO-3166 alpha-2 via `pycountry`.
  Stream-1 country filter payload is the full list. Frontend list from
  `i18n-iso-countries`.

## Workflow
Spec-driven: brainstorming → spec (`docs/superpowers/specs/`) → plan
(`docs/superpowers/plans/`) → TDD. Keep secrets in `.env` (gitignored).
`scripts/kt.sh` is a local-only manual smoke-test client (gitignored).

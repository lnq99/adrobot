# Adrobot — Design Spec

**Date:** 2026-11-26
**Status:** Approved for planning
**Requirements (authoritative):** [`docs/task-ru.md`](../../task-ru.md) — the original ТЗ — plus the video demo (youtu.be/jNloscEWCjA) for Part 2 behavior.
**Verified API reference (derived, not a requirement):** [`docs/api-reference.md`](../../api-reference.md) — field names and payloads confirmed against the test stand.

A wrapper around the Keitaro Admin API with two parts: a **campaign creator**
(Part 1) and a **campaign editor** with draft/publish semantics (Part 2).

---

## 1. Scope

**In scope**
- Part 1: create a campaign with two streams (geo→Google, offer) using a
  configured domain / group / traffic source.
- Part 2: edit offers in a campaign's streams — add, remove, bring back, pin,
  with weight rebalancing, draft/publish (push/cancel), archive, reverse-sync
  (REM), and push-time conflict detection.
- React SPA frontend; FastAPI backend; Postgres via Docker; Alembic migrations.

**Out of scope**
- User auth / multi-tenant (each key sees only its own campaigns on the stand).
- Clicks, stats, landings, triggers, postbacks (not on the stand).
- Creating offers/domains/groups/sources (catalog is read-only).

**Mandated by the task:** FastAPI + SQLAlchemy; README covering migrations and
running; public GitHub repo; campaign names prefixed `test_<surname>_`.

---

## 2. Architecture

```
React SPA (GitHub Pages) ──HTTP/JSON──► FastAPI backend ──HTTP──► Keitaro Admin API
      (VITE_API_URL, default                  │
       http://localhost:8000)                 ▼
                                        Postgres (Docker)
                                        drafts · offer state · snapshots
```

**Source-of-truth rule:** Keitaro owns *published* data. Our DB owns the *draft*,
*local offer state* (removed/pinned), *published snapshots* (for Cancel), and the
*last-seen Keitaro signature* (for conflict detection).

**Layers** (each independently testable):

| Layer | Responsibility | Depends on |
|-------|---------------|------------|
| `api/` routers | HTTP endpoints, request/response schemas, error mapping | services |
| `services/` | creator, editor, sync, publisher | keitaro client, repositories |
| `services/shares.py` | **pure** weight-rebalance function, no I/O | nothing |
| `keitaro/` | async httpx client + `FakeKeitaro` for tests | httpx |
| `models/` + `repositories/` | SQLAlchemy models + data access | DB session |
| `core/` | config (pydantic-settings), DB session, exceptions | — |

**Stack:** FastAPI, async `httpx` (Keitaro client), **sync** SQLAlchemy 2.0 +
`psycopg`, Alembic, pydantic-settings, pytest. CORS allows the GitHub Pages
origin + `localhost`.

---

## 3. Data model

```
campaigns
  id (pk)                     keitaro_campaign_id (unique)
  name                        alias            # Keitaro URL slug, display/link only
  geos (JSON: list[str])      created_at
  # the Part-1 offer is not stored here — it lives in offer_states under stream 2

streams
  id (pk)                     campaign_id (fk)
  keitaro_stream_id (unique)  position
  kind: "offers" | "opaque"   # opaque = non-offer streams (geo→Google): stored, not parsed
  is_dirty (bool)             # true = unpublished changes (UI shows yellow)
  published_snapshot (JSON)   # last-pushed offer set, for Cancel
  keitaro_signature (str)     # hash of Keitaro's last-seen state, for conflict detection

offer_states                  # only for kind="offers" streams
  id (pk)                     stream_id (fk)
  keitaro_offer_id            offer_name
  share (int)                 # current draft weight (0..100)
  status: "active" | "removed"
  origin: "local" | "keitaro" # only meaningful when removed; "keitaro" => REM badge
  pinned (bool)               # only meaningful when active
  published_share (int)       # weight at last publish (Cancel/diff)
```

Notes:
- `offer_states` is the editable draft. `published_snapshot` + `published_share`
  capture the last published state so **Cancel** restores it and
  added-but-never-published offers disappear.
- `kind="opaque"` preserves non-offer streams in `position` order without parsing
  their internals (per the video).

---

## 4. Offer state machine & weight rebalance

### State machine
```
                 add offer
   (not present) ─────────► active ◄───────────┐
                              │  ▲              │ bring back
                       remove │  │ pin/unpin    │
                              ▼  │ (self-loop)  │
                           removed ─────────────┘
                           (gray, share 0, archived)

   origin = "local"    → user clicked Remove
   origin = "keitaro"  → offer vanished from Keitaro (detected on fetch) → "REM" badge
```
- `active` participates in weights. `removed` is gray with `share=0`; both origins
  support **Bring back** → `active`.
- `pinned` is a flag on an `active` offer; ignored once removed.

### Rebalance — pure function `rebalance(offers) -> offers`
No I/O; unit-tested first (TDD).
**Mental model:** a *pinned* offer has a **user-controlled** share; *unpinned*
active offers evenly split whatever remains.

1. `removed` offers → `share = 0`.
2. `pinned` active offers keep their **user-set** `share` (editable; see §6).
3. `remain = 100 − Σ(pinned shares)`; split evenly (integer division) across
   unpinned-active offers.
4. Distribute the division remainder one point at a time to the first offers so
   the total is exactly 100.
5. Reject with 422 if `Σ(pinned shares) > 100`, if a pinned share is outside
   `0..100`, or if pins leave no room for existing unpinned-active offers
   (do not silently clamp).

**Canonical cases (become unit tests):**

| Input | Result |
|-------|--------|
| 4 active, none pinned | `25 / 25 / 25 / 25` |
| 3 active, none pinned | `34 / 33 / 33` |
| pin A@25, + B, C | `25 (pinned) / 38 / 37` |
| pin A@40 (user-set), B, C | `40 (pinned) / 30 / 30` |
| pin A@60, pin B@50 (Σ pinned > 100) | 422 error |

---

## 5. Part 1 — Campaign creator

`POST /api/campaigns`, input: `name`, `geos: list[str]`, `offer_id`.

1. **Validate:** every geo is a real ISO 3166-1 alpha-2 code (`pycountry`);
   `offer_id` exists (`GET /offers/{id}`); name carries the `test_<surname>_` prefix.
2. **Resolve** domain / group / traffic source via API (`/domains`,
   `/groups?type=campaigns`, `/traffic_sources`), with config fallback to the
   stand defaults (domain `1813`, group `10332`, source `836`).
3. **Create campaign:** `POST /campaigns`
   `{type:"position", group_id, traffic_source_id, domain_id, state:"active"}`.
   Note the field is **`traffic_source_id`** (verified: `source_id` is ignored).
4. **Create streams:**
   - Stream 1 (`regular`/`redirect`): filter `country accept <geos>` → `https://google.com`.
   - Stream 2 (`default`/`landings`): chosen offer @ `share=100`, `state="active"`.
5. **Rollback:** if any stream step fails, `DELETE` the campaign (no orphans).
6. **Persist** `campaigns` + both `streams` rows locally.

---

## 6. Part 2 — Campaign editor

| Flow | Endpoint | Behavior |
|------|----------|----------|
| **Fetch** | `POST /api/campaigns/{id}/fetch` | Pull streams from Keitaro. Parse only `schema=landings` streams; others stored `opaque`. Reconcile: known offers absent upstream → `removed, origin="keitaro"` (REM). Recompute `keitaro_signature`. |
| **Add offer** | `POST /api/streams/{sid}/offers` | Look up offer, insert `active`, `rebalance()`, `is_dirty=true`. |
| **Remove** | `DELETE /api/streams/{sid}/offers/{oid}` | `status=removed, origin="local"`, unpin, `rebalance()`, dirty. |
| **Bring back** | `POST /api/streams/{sid}/offers/{oid}/bring-back` | `status=active`, `rebalance()`, dirty. |
| **Pin / Unpin** | `POST /api/streams/{sid}/offers/{oid}/pin` `{pinned, share?}` | Toggle `pinned`; when pinning, `share` may set the locked value (default = current). `rebalance()`. Toggle alone → **not** dirty; **setting/changing a pinned share value → dirty** (it changes published weights). |
| **Push** | `POST /api/streams/{sid}/push` | Re-fetch Keitaro; if its signature ≠ stored → **409** (re-fetch required). Else validate Σ(active)=100, `PUT /streams/{sid}` with `offers`=active set, update snapshot/published_share/signature, `is_dirty=false`. |
| **Cancel** | `POST /api/streams/{sid}/cancel` | Restore `offer_states` from `published_snapshot`; drop never-published adds; `is_dirty=false`. |
| **Read** | `GET /api/campaigns/{id}/streams` | Return current draft state for the UI. |
| **Offer search** | `GET /api/offers?q=` | Autocomplete, proxies Keitaro. |
| **List** | `GET /api/campaigns` | Local campaigns. |

Push sends only `active` offers; `removed` offers stay in our DB (archive) but are
absent from Keitaro — exactly matching the "disappears from Keitaro, stays gray in
our tool" behavior.

---

## 7. Frontend (React + TypeScript SPA → GitHub Pages)

- **Views:** **Create** (name, multi-select countries, offer picker) and
  **Editor** (campaign list → stream cards → offer tables).
- **Visual state** (mirrors the ТЗ): stream card **yellow** when `is_dirty`; offer
  row **gray** when `removed`, with a **"REM"** badge when `origin="keitaro"`;
  **📌** on pinned offers; per-offer share % with a live running total.
- **Buttons:** Add, Remove, Bring back, Pin, Push, Cancel, Fetch.
- **Config:** API base URL from `VITE_API_URL` (build-time), default
  `http://localhost:8000` so the Pages build targets the reviewer's local backend.
- **Tooling:** Vite, TanStack Query for server state, light styling. Country list
  from `i18n-iso-countries` (single ISO source shared conceptually with the
  backend's `pycountry` validation).

---

## 8. Error handling

Typed exceptions mapped to consistent JSON `{error, detail}`:

| Condition | Status |
|-----------|--------|
| Validation (bad geo, Σ≠100, pin>100) | 422 |
| Not found (campaign/stream/offer) | 404 |
| Push conflict (Keitaro changed underneath) | 409 |
| Keitaro upstream failure | 502 |

The API key is never included in responses or logs.

---

## 9. Testing (TDD)

Written in this order, all against an in-memory `FakeKeitaro` + a test Postgres
(transactional rollback per test); no live-stand dependency in CI.

1. `test_shares.py` — pure rebalance (canonical cases, pin, remainder, over-100). **First.**
2. `test_creator.py` — two-stream creation, rollback on failure, reject bad offer/geo.
3. `test_editor.py` — add/remove/bring-back/pin, dirty transitions.
4. `test_sync.py` — reverse-sync REM (`origin="keitaro"`).
5. `test_publisher.py` — push validates Σ=100, conflict→409, cancel restores snapshot.
6. `test_walkthrough.py` — full video scenario end-to-end.

---

## 10. Acceptance criteria (video scenario)

1. Create campaign (multi-geo, 1 offer) → 2 streams, offer @100%.
2. A stream with 3 offers shows `34/33/33`; add a 4th → `25/25/25/25`, stream yellow.
3. Push → Keitaro has 4 offers; stream no longer yellow.
4. Add offer → Cancel → the added offer disappears; back to published state.
5. Remove an offer → gray, 0%, yellow → Push → gone from Keitaro, still gray (archive) locally.
6. Bring back → active → Push → back in Keitaro.
7. Delete an offer directly in Keitaro → Fetch → that offer becomes `removed/origin=keitaro` (REM, gray), not lost.
8. Pin an offer @25% → add/remove others → pinned stays 25%, the rest fill to 100%.
9. Edit a stream in Keitaro while holding a draft → Push → 409, prompt to re-fetch.

# Keitaro test stand — verified API reference

Compiled from `test-stand-ru.md` + the OpenAPI spec (`admin-api.openapi.json`).
How Adrobot uses these endpoints is in the design spec
[`docs/superpowers/specs/2026-11-26-adrobot-design.md`](./superpowers/specs/2026-11-26-adrobot-design.md).

**Provenance — verified by live calls** (via [`scripts/kt.sh`](../scripts/kt.sh)):
- create-campaign / two-streams / fetch / delete path, and the `traffic_source_id`
  gotcha (`source_id` is silently ignored);
- **`PUT /streams/{id}` replaces the whole offer list** (tested: 2 offers → `PUT`
  with 1 → stream has exactly 1);
- **no archive** — after `DELETE /campaigns/{id}`, `GET` returns "Campaign not found".

Still from stand docs only (not independently tested): `enable`/`disable`.

## Connection

| Item | Value |
|------|-------|
| Base URL | `https://keitaro-for-tests.etolegko.com/admin_api/v1` |
| Admin UI | `https://keitaro-for-tests.etolegko.com/admin/` (GitHub login; username = nick) |
| Auth | Header `Api-Key: <key>` (from the "API key" button in admin) |
| Campaign link in UI | `…/admin/#!/campaign.editor/<id>` |
| Scope | You only see **your own** campaigns |
| Request log | The admin UI logs **every** wrapper request (path, body, status); the reviewer sees the same log |

Put the key in `.env` (`KEITARO_API_KEY=…`, `KEITARO_BASE_URL=…`); see
[`.env.example`](../.env.example). `scripts/kt.sh` also accepts the colon format
(`Api-Key: …`).

## Fixed catalog IDs on the stand (verified)

| Entity | ID | Notes |
|--------|----|-------|
| Domain | **1813** | `domain: "https://kt-emulator.test/"` |
| Campaign group `FORTESTS` | **10332** | `GET /groups?type=campaigns` |
| Traffic source `FORTESTS` | **836** | `GET /traffic_sources` |
| Offers | ~170, ids from **18001** | read-only; e.g. `18001 Detoxin [HAIR-CL]…`, `country:["CL"]` |

> These are real, fixed values for this stand — hardcoding them is not a logic
> error. Resolving them via API (`/domains`, `/groups`, `/traffic_sources`) is
> preferred for portability.

## Supported endpoints (anything else returns an error)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/campaigns` | yours, newest first; `offset`, `limit` |
| POST | `/campaigns` | `name` required; `alias` auto-generated if omitted |
| GET/PUT/DELETE | `/campaigns/{id}` | PUT patches only sent fields; DELETE removes campaign + streams (**no archive**) |
| POST | `/campaigns/{id}/enable` · `/disable` | |
| GET | `/campaigns/{id}/streams` | ordered by `position` |
| POST | `/streams` | `campaign_id`, `name` required |
| GET/PUT/DELETE | `/streams/{id}` | **PUT: `offers` replaces all offers, `filters` replaces all filters** |
| POST | `/streams/{id}/enable` · `/disable` | |
| GET | `/offers`, `/offers/{id}` | read-only |
| GET | `/groups?type=campaigns`, `/domains`, `/traffic_sources` | read-only |

**Not available:** clicks/stats, landings/triggers/postbacks, deleted-item
archive, reference lists (`/stream_filters`, `/stream_types`, …) — use literal values.

## Verified payloads

### Create campaign — `POST /campaigns`
```json
{ "name": "test_<surname>_...", "type": "position",
  "group_id": 10332, "traffic_source_id": 836, "domain_id": 1813, "state": "active" }
```
Response includes `id`, auto `alias`, `group_id`, `traffic_source_id`,
`domain_id`, `state`, `group:"FORTESTS"`.

> ⚠️ **Gotcha (verified live):** the source field is **`traffic_source_id`**, not
> `source_id`. Sending `source_id` is silently ignored and the campaign's source
> stays `null`. The task requires the source to be configured, so use
> `traffic_source_id`.

### Stream 1 — country → Google — `POST /streams`
```json
{ "campaign_id": <id>, "name": "Geo GM", "type": "regular", "schema": "redirect",
  "action_type": "http", "action_payload": "https://google.com",
  "filters": [{ "name": "country", "mode": "accept", "payload": ["GM"] }] }
```
The country filter `payload` is an **array**, so multiple countries are supported
in one filter (e.g. `["GM", "FR"]`) — Adrobot's Part 1 takes a multi-select geo list.

### Stream 2 — offers — `POST /streams`
```json
{ "campaign_id": <id>, "name": "Offers", "type": "default", "schema": "landings",
  "offers": [{ "offer_id": 18001, "share": 100, "state": "active" }] }
```

### Offer shape inside a stream (for Part 2 parsing)
```json
{ "id": 1128, "stream_id": 733, "offer_id": 18001,
  "state": "active", "share": 100, "created_at": "…", "updated_at": "…" }
```
- Stream **with offers** = `schema:"landings"`, non-empty `offers` → parse in detail.
- Stream **without offers** (redirect→Google) = `offers:[]` → add as opaque, don't parse.
- **Push (Part 2)** = `PUT /streams/{id}` with `offers` = the **whole** list of
  `active` offers (full replacement).
- **Reverse-sync REM**: compare known offer_ids against the returned `offers`;
  missing ⇒ mark `rem` locally (never hard-delete).

## Smoke-test client: `scripts/kt.sh`

```bash
./scripts/kt.sh offers [limit]
./scripts/kt.sh domains | groups | sources
./scripts/kt.sh campaigns
./scripts/kt.sh streams <campaign_id>
./scripts/kt.sh create-campaign <name> [geo] [offer_id]
./scripts/kt.sh delete-campaign <id>
./scripts/kt.sh walkthrough <surname> [geo] [offer_id]   # create → fetch → cleanup
./scripts/kt.sh raw GET /offers/18001
```
Reads the key from `.env`, pretty-prints with `jq` if available. Campaign names
should carry the `test_<surname>_` prefix.

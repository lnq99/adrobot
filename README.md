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

🚧 Pre-implementation. Requirements and design live in [`docs/`](./docs); the
spec and implementation plan are being produced via a brainstorming workflow and
will land in [`docs/superpowers/`](./docs/superpowers).

## Docs

| File | What |
|------|------|
| [`docs/task-ru.md`](./docs/task-ru.md) | Original task (RU) |
| [`docs/api-reference.md`](./docs/api-reference.md) | **Verified** test-stand API reference |
| [`docs/test-stand-ru.md`](./docs/test-stand-ru.md) | Test-stand (emulator) access notes |
| [`docs/admin-api.openapi.json`](./docs/admin-api.openapi.json) | Keitaro Admin API OpenAPI spec |

The spec and implementation plan will be added under
[`docs/superpowers/`](./docs/superpowers) during brainstorming.

## Setup

```bash
cp .env.example .env     # then paste your Api-Key
```

## Test the stand

`scripts/kt.sh` is a smoke-test client for the Keitaro emulator (reads the key
from `.env`):

```bash
./scripts/kt.sh offers 5
./scripts/kt.sh walkthrough <surname> GM 18001   # create → fetch → cleanup
```

## Run (to be filled during implementation)

```bash
# alembic upgrade head
# uvicorn app.main:app --reload
# pytest
```

## How AI agents were used

This project was developed with Claude Code using a spec-driven workflow
(brainstorming → spec → plan → TDD). The resulting spec and implementation plan
are tracked under [`docs/superpowers/`](./docs/superpowers); the agent's project
instructions are in [`CLAUDE.md`](./CLAUDE.md).

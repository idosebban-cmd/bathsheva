# Product Workbench

A local web app for AI-assisted product engineering of physical consumer products. The first product is Faro, a lighthouse table lamp. `SPEC.md` has the full vision. **Only Milestone 1 (SPEC §12) is built.** Later sections shape the data model, but nothing outside M1 is implemented.

## Run

```bash
./run.sh          # first run creates backend/.venv and installs npm deps, then starts both servers
./run.sh test     # backend pytest + front-end typecheck
```

- Front end: http://127.0.0.1:5173. Vite proxies `/api` and `/files` to the backend on :8000.
- The LLM is optional. Set `ANTHROPIC_API_KEY` to enable the Anthropic provider. `WORKBENCH_LLM_PROVIDER=mock|anthropic|none` overrides the choice. With no key the provider is `none` and everything except "Explain with AI" works.
- Other environment variables: `WORKBENCH_DATA_DIR` (default `./data`), `WORKBENCH_DATABASE_URL`, `WORKBENCH_ANTHROPIC_MODEL` (default `claude-opus-5-5`; explanations use low effort plus server-side refusal fallback).
- Requirements: Python 3.10–3.13 (for CadQuery wheels) and Node 18+.

## Architecture

```
frontend/            Vite + React + TS. Pages per tab, react-three-fiber GLB viewer
backend/app/
  main.py            FastAPI app factory, mounts routers and /files/projects static
  config.py          Settings from env
  db.py              SQLAlchemy engine/session; init_db() runs migrations
  migrate.py         Alembic upgrade at startup (+ adopts pre-migration DBs)
  models.py          ORM. M1 tables plus schema-only later entities
  schemas.py         Pydantic API schemas (Requirements etc.)
  api/               Thin HTTP routers, one per area
  services/          Orchestration: projects, BOM, DFM, revisions
  rules/             Rules engine: loads seed YAML, produces recommendations
  cad/               CadQuery generators, parameter validation, export
  ai/                LLM provider abstraction (anthropic | mock | none)
backend/seed/
  rules/*.yaml       Engineering rules and cost data (editable)
  products/faro.yaml Faro template: parts, requirements placeholders, CAD defaults
backend/migrations/  Alembic env and versions/ (one file per schema change)
scripts/             stress_cad.py (CAD soak test), check_run_shutdown.py (run.sh stop behaviour)
data/                Runtime: SQLite DB, uploads, CAD outputs (gitignored)
```

Boundaries: routers handle only HTTP. The rules engine is pure, with no DB access: it takes plain dicts and returns recommendations. The CAD module never imports the DB. The AI layer only explains recommendations the rules engine has already made, and never changes them.

## Database migrations (Alembic)

On startup the app migrates the database to the latest revision (`app/migrate.py`). It never uses `create_all`. A database created by Milestone 1 before migrations existed (no `alembic_version` table) is stamped at the baseline `0001` and then upgraded, so its data is kept.

To change the schema:

1. Edit `backend/app/models.py`.
2. From `backend/`, generate a migration: `.venv/bin/alembic revision --autogenerate -m "add supplier rating"`. It uses `WORKBENCH_DATABASE_URL` / `WORKBENCH_DATA_DIR`, and that database must already be at head.
3. Review the new file in `backend/migrations/versions/`. Autogenerate can miss renames and data moves, and SQLite changes run in batch mode.
4. Run `./run.sh test`. `tests/test_migrations.py` fails if migrating a fresh database doesn't produce exactly the schema in `models.py`, or if there is more than one head.
5. Commit the model change and the migration together.

Other useful commands, run from `backend/`: `.venv/bin/alembic current`, `.venv/bin/alembic check` (reports any model change that has no migration), and `.venv/bin/alembic downgrade -1`.

## Process management

`run.sh` signals only its own two servers. Ctrl-C or SIGTERM is a clean stop (exit 0). If a server dies unexpectedly, `run.sh` stops the other one and exits with the dead server's status. Never use `kill 0` in a trap that also handles TERM: it re-enters itself and bash segfaults (exit 139). After changing `run.sh`, run `backend/.venv/bin/python scripts/check_run_shutdown.py`.

## Front-end tabs and API

| Tab | Endpoints (`/api/projects/{id}/…`) |
|---|---|
| Projects | `GET/POST /api/projects` (template `faro` seeds parts, requirements and CAD defaults) |
| Overview | `PATCH /api/projects/{id}`, `POST /images` |
| Parts | `GET/POST/PATCH/DELETE /parts` |
| CAD | `GET /cad`, `POST /cad/validate`, `POST /cad/generate`, `GET /cad/models/{v}/download.zip`; files under `/files/projects/...` |
| Engineering | `GET /recommendations`, `POST /recommendations/{part}/explain` (LLM), `POST /decisions` |
| BOM | `GET /bom`, `GET /bom.csv` |
| DFM report | `GET /dfm`, `GET /dfm.md` |
| Revisions | `GET/POST /revisions`, `GET /revisions/{n}` (no update or delete) |

Manufacturing and Factory Pack tabs, cost modelling, compliance and factory feedback are later milestones. Their tables exist in `models.py` but have no API.

## Rules engine in brief

For each candidate process in the part's material family, the engine applies hard exclusions first: missing required traits, excluded traits, or a wall thickness the process can't make. It then scores what's left on trait fit, volume fit, tooling cost, cosmetic finish need and finish compatibility. The best material is the one most often paired with the process that suits the target finish. Confidence comes from the score margin. It drops to low when volume is assumed and the answer changes between 100, 1,000 and 10,000 units, and it is capped at medium while the data is unverified. Traits come from the part plus CAD-derived traits (`faro.derived_traits`, for example tapered vs constant_section).

## Conventions

- **Provenance:** every seed rule entry has `source`, `confidence` (low/medium/high) and `verified` (default `false`). The loader rejects entries without them. Values written from general knowledge use `source: model-generated`. Anything derived from unverified data must be flagged in the UI.
- **Safety:** a recommendation that could affect product safety carries `safety_flags` and is shown as "verify with human/manufacturer".
- **Assumptions:** placeholder requirements are listed in `project.assumed_fields` and shown with an Assumption badge. When an inferred value feeds the rules (for example, assumed volume when volume is TBD), it appears in the recommendation's `assumptions`.
- **Plain language first:** each recommendation leads with a non-engineer explanation, with technical detail underneath.
- **Units:** millimetres, degrees, GBP.
- **CAD:** one body per part. A part's `cad_key` equals the generator's body name. Every regeneration creates a new immutable `CadModel` version under `data/projects/<id>/cad/v<n>/`.
- **Revisions:** an immutable JSON snapshot (requirements, parameters, parts, decisions, recommendations, CAD version and its file paths). No branching.
- **Decisions:** `EngineeringDecision.status` is one of proposed / accepted / rejected / edited.
- Tests live in `backend/tests`. Add tests with every rules, CAD, model or export change.
- Commit after each working vertical slice.

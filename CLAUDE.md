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
  costing/           Cost model: data.py (seed loader), model.py (pure calculation),
                     assemble.py (snapshot + config -> inputs), pricing.py (retail -> target factory cost)
backend/seed/
  rules/*.yaml       Engineering rules (editable)
  cost/*.yaml        Cost rates: material £/kg, process rates, finishes, labour, bought-in prices,
                     regions, route design changes, channel pricing
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
| Parts | `GET/POST/PATCH/DELETE /parts`; quotes `GET/POST /parts/{part}/quotes`, `DELETE /quotes/{id}`; `GET /quote-pack.zip` |
| CAD | `GET /cad`, `POST /cad/validate`, `POST /cad/generate`, `GET /cad/models/{v}/download.zip`; files under `/files/projects/...` |
| Engineering | `GET /recommendations`, `POST /recommendations/{part}/explain` (LLM), `POST /decisions` |
| BOM | `GET /bom`, `GET /bom.csv` |
| Manufacturing | `GET /costs`; `GET/POST /cost-items`, `PATCH/DELETE /cost-items/{id}`, `POST /cost-items/reset` |
| Cost-down | `GET/PUT /pricing`; `GET /routes`, `POST /parts/{part}/route`; `GET /scenarios`, `POST /scenarios/evaluate`; `GET /cost-down/summary`; `GET/POST /scenario-sets`, `DELETE /scenario-sets/{id}` |
| DFM report | `GET /dfm`, `GET /dfm.md` |
| Revisions | `GET/POST /revisions`, `GET /revisions/{n}` (no update or delete) |

The Factory Pack tab, compliance and factory feedback are later milestones. Their tables exist in `models.py` but have no API.

## Rules engine in brief

For each candidate process in the part's material family, the engine applies hard exclusions first: missing required traits, excluded traits, or a wall thickness the process can't make. It then scores what's left on trait fit, volume fit, tooling cost, cosmetic finish need and finish compatibility. The best material is the one most often paired with the process that suits the target finish. Confidence comes from the score margin. It drops to low when volume is assumed and the answer changes between 100, 1,000 and 10,000 units, and it is capped at medium while the data is unverified. Traits come from the part plus CAD-derived traits (`faro.derived_traits`, for example tapered vs constant_section).

## Cost model in brief

`app/costing/model.py` is pure. Each input is a named `Assumption` (low/high plus provenance). Per part: material is CAD volume × density × scrap factor (CNC uses bar stock), process is cycle minutes × machine rate, setup and tooling are divided by the quantity, and finishing is max(minimum charge, visible area × rate). Product-level lines (bought-in parts, assembly minutes × labour rate, packaging) are editable `CostItem` rows, seeded from `faro.yaml` `cost_items` for the current power type.

Ranges: each input is widened by its confidence (`seed/cost/general.yaml` `confidence_spread`; verified inputs are not widened). The range is the midpoint ± the root-sum-square of each input's effect, and the all-worst-case envelope is also reported. Sensitivity moves each assumption ±25% and ranks by unit-cost swing. Process and material come from the part's decision, else the rules recommendation. When a part's manual cost fields are blank, quotes are compared with the model's estimate at the quote's quantity.

## Cost-down in brief

`services/costing.snapshot()` reads the project once. `costing/assemble.assemble(snapshot, CostConfig)` builds model inputs for any configuration: route overrides, removed parts, added or removed items, assembly-time change, height, region, and material or finish overrides. It's pure and takes about 0.3 ms, so routes and scenarios are evaluated by assembling, never by changing the database.

- **Routes:** every `viable` process from the rules engine is costed per part. `seed/cost/route_changes.yaml` adds the design changes and extra parts a route needs; these are costed wherever that route is used (current configuration, route table, scenarios). Selecting a route records a `process_route` decision and sets the part's process and material. CAD is never changed. `costdown.cad_mismatches()` drives the "CAD no longer matches" flags in the BOM and DFM.
- **Sheet-formed parts** (spun, pressed, rolled) are costed as a shell of the CAD wall thickness when the CAD body is solid.
- **Scenarios** live in `faro.yaml` `scenarios`. The optimiser searches every non-conflicting subset and every region exhaustively. Each multi-option change uses its cheapest option on its own, which is valid because options touch only their own part (a test checks this against brute force). There are three tiers by `premium_impact`: strict (none), premium (none or slight) and any.
- **Pricing:** `projects.pricing` overlays defaults from `seed/cost/pricing.yaml` plus the template. DTC target = ex-VAT × dtc share. Retail-channel target = ex-VAT × (1 − retailer margin) × wholesale share. Status: pass ≤ target, close ≤ target × (1 + close band), otherwise fail.
- **Migrations on SQLite** run with foreign keys off (`app/migrate.py`), because batch rebuilds would otherwise cascade-delete child rows.

## Conventions

- **Provenance:** every seed rule entry has `source`, `confidence` (low/medium/high) and `verified` (default `false`). The loader rejects entries without them. Values written from general knowledge use `source: model-generated`. Anything derived from unverified data must be flagged in the UI.
- **Safety:** a recommendation that could affect product safety carries `safety_flags` and is shown as "verify with human/manufacturer".
- **Assumptions:** placeholder requirements are listed in `project.assumed_fields` and shown with an Assumption badge. When an inferred value feeds the rules (for example, assumed volume when volume is TBD), it appears in the recommendation's `assumptions`.
- **Plain language first:** each recommendation leads with a non-engineer explanation, with technical detail underneath.
- **Units:** millimetres, degrees, GBP.
- **CAD:** one body per part. A part's `cad_key` equals the generator's body name. Every regeneration creates a new immutable `CadModel` version under `data/projects/<id>/cad/v<n>/`.
- **Revisions:** an immutable JSON snapshot (requirements, parameters, parts, decisions, recommendations, CAD version and its file paths). No branching.
- **External quotes:** real supplier quotes and DFM feedback (`ExternalQuote`) are for the user to review against the part's estimated unit-cost range. They never change the rules engine, seed data or part fields automatically. Seed data is updated by hand. The comparison doesn't convert currencies. The quote pack includes only manufactured parts; bought-in parts and hardware are listed in its README.
- **Decisions:** `EngineeringDecision.status` is one of proposed / accepted / rejected / edited.
- Tests live in `backend/tests`. Add tests with every rules, CAD, model or export change.
- Commit after each working vertical slice.

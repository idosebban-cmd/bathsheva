# Product Workbench

A local web app for AI-assisted product engineering of physical consumer products. The first product is Faro, a cordless lighthouse table lamp. `SPEC.md` has the full vision.

**Faro's design source of truth** is the approved prototype on branch `claude/rocket-speaker-3d-model-xav3pn` (`faro/lamp.py`, `faro/params.py`, renders and build manual). Never modify that branch. The workbench generator ports its form, proportions and features (spiral windows, frosted diffusers, gallery and railing, twist-lock cap), adapted for production in metal. Every departure from the prototype is listed in `faro.PRODUCTION_CHANGES` (shown in the CAD tab and the RFQ). Don't change the design silently: add a row there. **Only Milestone 1 (SPEC §12) is built.** Later sections shape the data model, but nothing outside M1 is implemented.

## Run

```bash
./run.sh          # first run creates backend/.venv and installs npm deps, then starts both servers
./run.sh test     # backend pytest + front-end typecheck + front-end unit tests (Node 22.6+)
```

On a Mac, `bash scripts/setup_mac.sh` does the whole setup. It asks before installing the Xcode command line tools, Homebrew, uv or Node.js LTS, and it supports `--dry-run` and `--yes`. It builds the venv with uv on pinned Python 3.12, which has build123d/OpenCASCADE wheels for both Apple Silicon and Intel (macOS 12+). It removes CadQuery from an older venv and reinstalls build123d's OCP package, because both ship an `OCP` module. It then migrates the database (backing it up first if a migration is pending) and runs a CAD self-test in a temporary folder (`scripts/workbench_check.py`). It is safe to re-run. After that, double-click `Start Workbench.command`. README.md has the user-facing steps. `WORKBENCH_SETUP_ALLOW_NON_MAC=1` runs the non-macOS parts on Linux for testing.

- Front end: http://127.0.0.1:5173. Vite proxies `/api` and `/files` to the backend on :8000.
- The LLM is optional. Set `ANTHROPIC_API_KEY` to enable the Anthropic provider. `WORKBENCH_LLM_PROVIDER=mock|anthropic|none` overrides the choice. With no key the provider is `none` and everything except "Explain with AI" works.
- Other environment variables: `WORKBENCH_DATA_DIR` (default `~/Bathsheva Workbench/data`, outside the repo; `app/datadir.py` moves a legacy in-repo `data/` there once, when the default is used and the target is empty), `WORKBENCH_DATABASE_URL`, `WORKBENCH_ANTHROPIC_MODEL` (default `claude-opus-5-5`; explanations use low effort plus server-side refusal fallback).
- Requirements: Python 3.10–3.13 (for the OpenCASCADE wheels; `run.sh` and the Mac setup create the venv on 3.12) and Node 18+.

## Architecture

```
frontend/            Vite + React + TS. Pages per tab, react-three-fiber GLB viewer
backend/app/
  main.py            FastAPI app factory, mounts routers and /files/projects static
  config.py          Settings from env
  datadir.py         Data folder location and the one-time move out of the repo
  db.py              SQLAlchemy engine/session; init_db() runs migrations
  migrate.py         Alembic upgrade at startup (+ adopts pre-migration DBs)
  models.py          ORM. M1 tables plus schema-only later entities
  schemas.py         Pydantic API schemas (Requirements etc.)
  api/               Thin HTTP routers, one per area
  services/          Orchestration: projects, BOM, DFM, revisions, decisions (template-accepted
                     decisions), factory_pack (RFQ pack), electrical (runtime), template_upgrade
  factory/           drawings.py: 2D quotation drawings (reportlab -> SVG + PDF), sectioned from the built solids
  rules/             Rules engine: loads seed YAML, produces recommendations
  cad/               build123d generators (faro.py), parameter validation, export (STEP/STL/GLB)
  electrical.py      Battery runtime from the battery spec and LED loads (pure)
  ai/                LLM provider abstraction (anthropic | mock | none)
  costing/           Cost model: data.py (seed loader), model.py (pure calculation),
                     assemble.py (snapshot + config -> inputs), pricing.py (retail -> target factory cost)
backend/seed/
  rules/*.yaml       Engineering rules (editable)
  rules/constraints.yaml  Design constraints (visible parts solid metal) enforced by engine + optimiser
  cost/*.yaml        Cost rates: material £/kg, process rates, finishes, labour, bought-in prices,
                     regions, route design changes, channel pricing, commodities (LME, FX, premiums)
  products/faro.yaml Faro template: parts, requirements placeholders, CAD defaults
backend/migrations/  Alembic env and versions/ (one file per schema change)
scripts/             stress_cad.py (CAD soak test), build_factory_pack.py (docs/factory-pack), check_run_shutdown.py (run.sh and launcher stop behaviour),
                     cost_audit.py (regenerates docs/cost-assumptions-audit.md),
                     setup_mac.sh + mac_env.sh + workbench_check.py (Mac setup, PATH, migrate/self-test)
Start Workbench.command  Double-click launcher for macOS (wraps run.sh, opens the browser)
docs/                Generated reports (cost-assumptions-audit.md) and cost-price-research.md
~/Bathsheva Workbench/data   Runtime: SQLite DB, uploads, CAD outputs (outside the repo)
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

Other useful commands, run from `backend/`: `.venv/bin/alembic current` and `.venv/bin/alembic check` (reports any model change that has no migration). Don't use `alembic downgrade` or `alembic upgrade` from the CLI yet (see the known issue below).

**Known issue (not fixed): CLI `alembic upgrade` / `downgrade` don't persist on SQLite.** They log `Running downgrade 0005 -> 0004` (or upgrade) and exit 0, but `alembic current` is unchanged afterwards. This happens on an empty database too. On a database with projects, a failed `downgrade -1` leaves `_alembic_tmp_projects` behind, and retrying fails with `table _alembic_tmp_projects already exists`. A CLI upgrade leaves `_alembic_tmp_cost_items` the same way. Likely cause: in `migrations/env.py` `_run()`, the `PRAGMA foreign_keys=OFF` executed on a CLI connection autobegins a transaction, so Alembic's `begin_transaction()` defers to it and nothing commits before `engine.connect()` closes and rolls back. SQLite's partially autocommitted batch DDL explains the leftover temp tables. The app's startup path (`app/migrate.py`, which passes its own connection inside `conn.begin()`) is unaffected and still migrated such a database to head. `tests/test_migrations.py` doesn't cover the CLI. Until it's fixed, test downgrades through `alembic.command` with a connection in `cfg.attributes["connection"]` inside `engine.begin()`, as `app/migrate.py` does. Never run them on a real data folder without a backup.

## Process management

`run.sh` signals only its own two servers. Ctrl-C, SIGTERM or SIGHUP (Terminal window closed) is a clean stop (exit 0). `Start Workbench.command` runs `run.sh` in the background and forwards INT, HUP and TERM to it as TERM. If a server dies unexpectedly, `run.sh` stops the other one and exits with the dead server's status. Never use `kill 0` in a trap that also handles TERM: it re-enters itself and bash segfaults (exit 139). After changing `run.sh` or the launcher, run `backend/.venv/bin/python scripts/check_run_shutdown.py`, and shellcheck the shell scripts.

## Front-end tabs and API

| Tab | Endpoints (`/api/projects/{id}/…`) |
|---|---|
| Projects | `GET/POST /api/projects` (template `faro` seeds parts, requirements and CAD defaults), `DELETE /api/projects/{id}` (records cascade, then `data/projects/<id>/` is removed; the page confirms, naming the project and its times) |
| Overview | `PATCH /api/projects/{id}`, `POST /images`, `GET /runtime`, `GET/POST /template-upgrade` |
| Parts | `GET/POST/PATCH/DELETE /parts`; quotes `GET/POST /parts/{part}/quotes`, `DELETE /quotes/{id}`; `GET /quote-pack.zip` |
| CAD | `GET /cad`, `POST /cad/validate`, `POST /cad/generate`, `GET /cad/models/{v}/download.zip`; files under `/files/projects/...` |
| Engineering | `GET /recommendations`, `POST /recommendations/{part}/explain` (LLM), `POST /decisions` |
| BOM | `GET /bom`, `GET /bom.csv` |
| Manufacturing | `GET /costs`; `GET/POST /cost-items`, `PATCH/DELETE /cost-items/{id}`, `POST /cost-items/reset`; `GET/PUT /cost-settings` (volume discounts); `GET /cost-audit?quantity=500` (+ `.md`, `.csv`) |
| Cost-down | `GET/PUT /pricing` (incl. the DTC price stack); `GET /routes`, `POST /parts/{part}/route`; `GET /scenarios`, `POST /scenarios/evaluate`; `GET /cost-down/summary`; `GET/POST /scenario-sets`, `DELETE /scenario-sets/{id}` |
| DFM report | `GET /dfm`, `GET /dfm.md` |
| Factory Pack | `GET /factory-pack` (incl. consistency checks and open questions), `GET/PUT /factory-pack/contact`, `GET /factory-pack.zip`, `GET /drawings/{cad_key}.svg\|.pdf`, `GET /rfq.md\|.pdf`, `GET /rfq-electronics.md\|.pdf` |
| Revisions | `GET/POST /revisions`, `GET /revisions/{n}` (no update or delete) |

The Factory Pack tab has the first part of SPEC §5 (the RFQ pack). Compliance and factory feedback are later milestones; their tables exist in `models.py` but have no API.

## Rules engine in brief

For each candidate process in the part's material family, the engine applies hard exclusions first: missing required traits, excluded traits, or a wall thickness the process can't make. It then scores what's left on trait fit, volume fit, tooling cost, cosmetic finish need and finish compatibility. The best material is the one most often paired with the process that suits the target finish. Confidence comes from the score margin. It drops to low when volume is assumed and the answer changes between 100, 1,000 and 10,000 units, and it is capped at medium while the data is unverified. Traits come from the part plus CAD-derived traits (`faro.derived_traits`, for example tapered vs constant_section).

Design constraints (`seed/rules/constraints.yaml`): "visible parts must be solid metal" restricts the material kinds (metal, or glass for transparent parts) for parts with `cosmetic`/`transparent` traits; `hidden` parts and certified electrical / bought-in parts are exempt, and `visible_trim` bought-in parts get a supplier requirement (Faro's knob and finial are made in solid brass, so none by default). A process whose materials all break it appears in `excluded` with `constraint` set; metal-effect finishes are reported as violations. The cost-down optimiser never chooses a scenario option that breaks it (`costdown.option_allowed`).

## Cost model in brief

`app/costing/model.py` is pure. Each input is a named `Assumption` (low/high plus provenance). Per part: material is CAD volume × density × scrap factor (CNC uses bar stock), process is cycle minutes × machine rate, setup and tooling are divided by the quantity, and finishing is max(minimum charge, visible area × rate). Product-level lines (bought-in parts, assembly minutes × labour rate, packaging) are editable `CostItem` rows, seeded from `faro.yaml` `cost_items` for the current power type.

Price basis: material and bought-in seed entries carry `price_basis` (trade_volume / distributor_small_qty / retail / model_estimate) and `basis_quantity`. Distributor and retail prices with a `discount_class` are multiplied by a volume-discount assumption (`general.yaml` `volume_discount_*`, editable per project via `/cost-settings`) at `from_quantity` (500) and above. Outside the UK (`regions.yaml` `material_basis: trade`), sheet aluminium is priced from `commodities.yaml`: (LME + regional premium) / FX / 1000 + sheet conversion. `evaluate(..., raw=True)` and `raw_mid` give the cost at the researched basis, shown next to the adjusted cost. A price the user types into a cost item becomes `trade_volume` (no discount).

Ranges: each input is widened by its confidence (`seed/cost/general.yaml` `confidence_spread`; verified inputs are not widened). The range is the midpoint ± the root-sum-square of each input's effect, and the all-worst-case envelope is also reported. Sensitivity moves each assumption ±25% and ranks by unit-cost swing. Process and material come from the part's decision, else the rules recommendation. When a part's manual cost fields are blank, quotes are compared with the model's estimate at the quote's quantity.

## Cost-down in brief

`services/costing.snapshot()` reads the project once. `costing/assemble.assemble(snapshot, CostConfig)` builds model inputs for any configuration: route overrides, removed parts, added or removed items, assembly-time change, height, region, and material or finish overrides. It's pure and takes about 0.3 ms, so routes and scenarios are evaluated by assembling, never by changing the database.

- **Routes:** every `viable` process from the rules engine is costed per part. `seed/cost/route_changes.yaml` adds the design changes and extra parts a route needs; these are costed wherever that route is used (current configuration, route table, scenarios). Selecting a route records a `process_route` decision and sets the part's process and material. CAD is never changed. `costdown.cad_mismatches()` drives the "CAD no longer matches" flags in the BOM and DFM.
- **Sheet-formed parts** (spun, pressed, rolled) are costed as a shell of the CAD wall thickness when the CAD body is solid.
- **Accepted decisions** in `faro.yaml` `decisions` are recorded on new projects (`services/decisions.py`, idempotent). They cover:
  - spun base, tower and cap;
  - spun brass gallery (1 mm shell + soldered locating ring);
  - brass frame, spigot, finial and knob turned from near-net stock (`cnc_turning_near_net`: tube, ring blank or close bar; stock = finished volume × `stock_factor`);
  - photo-etched railing and nameplate;
  - cream band turned from near-net stock;
  - borosilicate lantern and opal diffuser (window zone only, on a spider on the tower-light spine);
  - cordless power;
  - bonded-and-screwed construction (no central rod).

  They are the baseline, not scenarios.
- **CAD mismatch** is computed at read time: a route decision's `design_change_keys` are checked against `faro.IMPLEMENTED_CHANGES` and the bodies in the latest generated model.
- **Power options** (`faro.yaml` `power_options`): A (cordless, 2 x 18650, USB-C) and B (scenario g: external adapter + DC-DC driver, no battery). The product summary optimises each separately; B always includes g.
- **Price points** (`faro.yaml` `pricing.price_points`, plus the planned retail price): the summary's `price_points` table shows the DTC and retail-channel factory targets at each retail price and how the current and best configurations (power A, 500 and 2,000) compare.
- **Scenarios** live in `faro.yaml` `scenarios`. The optimiser searches every non-conflicting subset and every region exhaustively. Each multi-option change uses its cheapest option on its own, which is valid because options touch only their own part (a test checks this against brute force). There are three tiers by `premium_impact`: strict (none), premium (none or slight) and any.
- **One-off costs:** cost items of kind `one_off` (lamp safety/EMC testing on both power options; custom-pack UN38.3/IEC 62133-2 testing in scenario c) are totals divided by the quantity, listed after freight and duty and never charged freight. The baseline battery is a pre-certified pack (supplier provides the reports).
- **Simplified premium** (scenario s, `edition: true`): gallery, railing and lantern frame in colour-matched lacquered aluminium (`effect.reroutes` + `effect.finishes`), brass only on the finial, knob and nameplate. The optimiser never picks an edition scenario; the summary's `editions` table costs it next to full detail (best strict) for each power option at 500 and 2,000.
- **DTC price stack:** `stack_*` pricing keys (freight/storage, delivery, payment % + fixed, returns %, marketing £/sale, other one-off £ total, profit %) plus VAT. `pricing.price_stack()` gives break-even and profit-target retail (inc. VAT): ex-VAT = per-unit costs / (1 − returns − payment × (1 + VAT) − profit).
- **Template decisions changed** (no part change) also trigger the Overview "Update to the current design" banner (`decisions.missing_template_decisions`).
- **Pricing:** `projects.pricing` overlays defaults from `seed/cost/pricing.yaml` plus the template. DTC target = ex-VAT × dtc share. Retail-channel target = ex-VAT × (1 − retailer margin) × wholesale share. Status: pass ≤ target, close ≤ target × (1 + close band), otherwise fail.
- **Migrations on SQLite** run with foreign keys off (`app/migrate.py`), because batch rebuilds would otherwise cascade-delete child rows.

## Conventions

- **Provenance:** every seed rule entry has `source`, `confidence` (low/medium/high) and `verified` (default `false`). The loader rejects entries without them. Values written from general knowledge use `source: model-generated`. Anything derived from unverified data must be flagged in the UI.
- **Safety:** a recommendation that could affect product safety carries `safety_flags` and is shown as "verify with human/manufacturer".
- **Assumptions:** placeholder requirements are listed in `project.assumed_fields` and shown with an Assumption badge. When an inferred value feeds the rules (for example, assumed volume when volume is TBD), it appears in the recommendation's `assumptions`.
- **Plain language first:** each recommendation leads with a non-engineer explanation, with technical detail underneath.
- **Units:** millimetres, degrees, GBP.
- **CAD:** one body per part. A part's `cad_key` equals the generator's body name. Faro has 21 bodies (spun base/tower/cap, spun brass gallery, turned brass frame/spigot/finial/knob, photo-etched railing and nameplate, glass lantern and diffuser, plates, felt, and placeholder electronics). `overall_height` runs from the base underside to the finial top; the felt adds 1.9 mm below. Revolved parts are built from 2D half-sections (`faro._sections`), and shells are an offset of the outer profile. Offset curves are converted to B-splines, because a revolved offset curve doesn't survive STEP. `faro.model()` caches one build per parameter set. Old saved parameters are upgraded with new defaults (`faro.upgrade`). Pre-prototype parameters (no `tower_bottom_diameter`) are replaced by the defaults. The tower's red section is the same part in two-tone lacquer. The GLB splits it into `tower` and `tower_lower` for the preview only. Every regeneration creates a new immutable `CadModel` version under `data/projects/<id>/cad/v<n>/`.
- **Cordless power:** baseline 2 x 18650 + USB-C (`requirements.power_type: battery`); option B (external adapter) is scenario g. `requirements.battery_runtime_h` is the editable runtime target; `faro.yaml` `electrical` holds the battery spec, LED loads (with provenance) and battery compliance flags shown in the Overview, DFM and RFQ.
- **Template upgrades:** projects created from an older template version keep their old parts until the user presses "Update to the current design" (Overview). `services/template_upgrade.py` removes old parts (with their quotes and decisions), adds new ones, updates the requirements the template now fixes, re-applies decisions and resets cost items.
- **Project timestamps:** the API sends `created_at` / `updated_at` as UTC (SQLite drops the zone; `schemas.ProjectSummary` restores it) and the front end shows them in UK local time (`frontend/src/format.ts`, tested with `npm test`, Node 22.6+). A `before_flush` hook in `models.py` touches the project's `updated_at` whenever any of its records change. A new project never inherits a leftover `data/projects/<id>/` (SQLite can reuse the last deleted id): it is moved to `projects/_orphaned/`.
- **Revisions:** an immutable JSON snapshot (requirements, parameters, parts, decisions, recommendations, CAD version and its file paths). No branching.
- **External quotes:** real supplier quotes and DFM feedback (`ExternalQuote`) are for the user to review against the part's estimated unit-cost range. They never change the rules engine, seed data or part fields automatically. Seed data is updated by hand. The comparison doesn't convert currencies. The quote pack includes only manufactured parts; bought-in parts and hardware are listed in its README.
- **Decisions:** `EngineeringDecision.status` is one of proposed / accepted / rejected / edited.
- **Factory Pack:** the zip has `mechanical/` (RFQ, drawings, STEP, supplier BOM without costs) and `electronics/` (separate RFQ: pre-certified 2 x 18650 pack with pass-through charging, control board with 2-channel dimming, LEDs). Quantities 300 / 500 / 2,000; brass parts are quoted two ways (preferred and near-net, `factory_pack.NEAR_NET_BASIS`). `consistency_checks()` compares the drawings' solids with the saved STEP volumes, each part's process with the one its drawing notes assume (`drawings.NOTE_PROCESS`), the geometry with `PRODUCTION_CHANGES` (`faro.production_change_checks`) and scans supplier documents for £ amounts. Supplier questions live in `faro.yaml` `rfq_open_questions` (resolved once they have an `answer`); what the RFQs state comes from `faro.yaml` `rfq` (first order, UKCA marking for the UK launch, FOB + DDP in GBP or USD, ISO 2768-m, AQL, colour hexes with approximate RAL, and the bracketed contact/address placeholders the user fills in). Contact and delivery details (`projects.rfq_contact`, `GET/PUT /factory-pack/contact`, edited in the Factory Pack tab) fill both RFQs; blank fields stay as placeholders and raise a warning-level check (`level: warn`, not a failure). **Nameplate lettering** (`app/factory/nameplate.py`): "FARO" in Cormorant Garamond SemiBold from the bundled `seed/fonts/` (OFL), cap height 5 mm, centred on its outline. Outlines come from the TTF via fontTools (not OpenCASCADE's font engine, which mangles this font), flattened to 0.063 mm polylines, with overlapping and self-crossing contours resolved by the nonzero winding rule. `scripts/export_nameplate_artwork.py` stores the loops (JSON) plus SVG and DXF in `seed/artwork/`. The same loops drive the vector files, the 3D etch (0.15 mm, cut per letter into a 0.5°-faceted plate shell, because the curved booleans fail; black fill is a preview-only GLB body `nameplate_fill`) and the drawing, and `nameplate.consistency()` checks all four. The viewer gives the faceted plate true cylinder normals (`materials.smoothFaceted`). **Knob logo** (`app/factory/logo.py`): the logo (half sun, seven rays, two waves) redrawn as parametric geometry from the reference image in `seed/artwork/reference/` (proportions are fractions of the medallion radius), engraved 0.2 mm into the knob face and filled black, medallion Ø16 mm with a rim groove, grooves 0.4 mm, upright at the knob's off stop. Stored loops (with the generating proportions, so the runtime check needn't rebuild) plus SVG and DXF in `seed/artwork/` (same export script). The engraved knob is cached per diameter (`faro._engraved_knob`); the black fill is the preview body `knob_logo_fill`; the knob drawing has a logo front view; `logo.consistency()` checks lines, files, model and drawing; engraving is a cost item (`knob_logo_engrave`) and an RFQ operation on the knob. **Finishes (Oct 2026):** base satin black 30–50 GU; cream and oxblood red gloss 80+ GU; all visible brass brushed satin and clear-lacquered, matching Atelier (`brushed_lacquer` finish in the rules and cost rates). The RFQ colours table and the supplier BOM carry hex (design reference), approximate RALs (red: RAL 3011 and RAL 3002) and gloss, and say the physical samples are the master. Preview materials live in `frontend/src/components/materials.ts`: the brushed grain is a roughness streak in the shader, because the GLB has no UVs. The template upgrade also updates part finishes that still carry an old template default (`template_upgrade.OLD_TEMPLATE_FINISHES`), never ones the user chose. `scripts/build_factory_pack.py` writes `docs/factory-pack/` (zip, consistency.md, open-questions.md) for the default design. Drawings cover made-to-drawing parts only (`drawings.DRAWN_PARTS`). Nothing sent to suppliers contains our cost estimates or targets. Mark unverified values (UNVERIFIED) and safety / compliance items in every drawing and the RFQ.
- Tests live in `backend/tests`. Add tests with every rules, CAD, model or export change.
- Commit after each working vertical slice.

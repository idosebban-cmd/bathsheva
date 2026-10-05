# Product Workbench

A local web app for AI-assisted product engineering of physical consumer products. The first product is Faro, a lighthouse table lamp. `SPEC.md` has the full vision. **Only Milestone 1 (SPEC §12) is built.** Later sections shape the data model, but nothing outside M1 is implemented.

## Run

```bash
./run.sh          # first run creates backend/.venv and installs npm deps, then starts both servers
./run.sh test     # backend pytest + front-end typecheck
```

- Front end: http://127.0.0.1:5173. Vite proxies `/api` and `/files` to the backend on :8000.
- The LLM is optional. Set `ANTHROPIC_API_KEY` to enable the Anthropic provider. `WORKBENCH_LLM_PROVIDER=mock|anthropic|none` overrides the choice. With no key the provider is `none` and everything except "Explain with AI" works.
- Other environment variables: `WORKBENCH_DATA_DIR` (default `./data`), `WORKBENCH_DATABASE_URL`, `WORKBENCH_ANTHROPIC_MODEL`.
- Requirements: Python 3.10–3.13 (for CadQuery wheels) and Node 18+.

## Architecture

```
frontend/            Vite + React + TS. Pages per tab, react-three-fiber GLB viewer
backend/app/
  main.py            FastAPI app factory, mounts routers and /files/projects static
  config.py          Settings from env
  db.py              SQLAlchemy engine/session; create_all (no migrations yet)
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
data/                Runtime: SQLite DB, uploads, CAD outputs (gitignored)
```

Boundaries: routers handle only HTTP. The rules engine is pure, with no DB access: it takes plain dicts and returns recommendations. The CAD module never imports the DB. The AI layer only explains recommendations the rules engine has already made, and never changes them.

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

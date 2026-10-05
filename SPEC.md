# Product Workbench: Specification

A local web application that acts as an AI-assisted product engineering and manufacturing workbench for physical consumer products.

**Objective:** concept → engineering decisions → parametric CAD → manufacturing package → supplier feedback → improved product.

The first product is **Faro**. The system must support unlimited future products.

This document describes the full vision. Only the section marked **Milestone 1** is in scope for the current build. Everything else informs the data model and architecture so later work fits without rewrites.

---

## 1. Core workflow (full vision)

1. Create a product project.
2. Upload concept renders and reference images.
3. Enter product requirements:
   - name, description
   - approximate dimensions
   - target retail price
   - expected production volume
   - target manufacturing cost
   - intended markets
   - power type: mains, battery or passive
   - preferred materials and finishes
   - functional requirements
   - environmental requirements
4. Analyse the product and propose, per part where relevant:
   - part breakdown
   - manufacturing process
   - materials and alloys
   - wall thicknesses
   - draft angles
   - bend radii
   - tolerances
   - fasteners and joining methods
   - internal structure
   - assembly sequence
   - finishing processes
   - manufacturing risks
5. Accept, reject or edit every recommendation.
6. Generate a structured product specification.
7. Generate a BOM.
8. Generate a manufacturing/DFM report.
9. Generate an RFQ package for manufacturers.
10. Maintain version history as the product changes.

---

## 2. Faro (first product)

A premium decorative electrical table lamp inspired by a lighthouse. Second product of Bathsheva London, after the Atelier speaker.

**Aesthetic:** smooth, sculptural, playful, premium, influenced by mid-century Italian product design. Never toy-like or cheap. Aimed at a middle-class, design-conscious customer rather than luxury buyers.

**Current material direction:**
- aluminium main body
- painted/lacquered coloured aluminium sections
- base finished in black lacquer (changed from walnut, Sept 2026)
- possible brass or brass-plated details
- transparent lantern section
- internal LED lighting
- power: mains or rechargeable, **undecided** (treat as an open project-level decision)

**Commercial inputs:** to be supplied by the user. Until then, seed with placeholder values that are visibly marked as assumptions:
- target retail price: TBD
- production volume: TBD
- target unit manufacturing cost: TBD
- intended markets: UK and EU
- approximate dimensions: TBD

**Process question per aluminium part:** spun, CNC machined, sheet formed, deep drawn, die cast, extruded, or other. Recommendations weigh geometry, quantity, tooling cost, unit cost, finish quality, strength, weight, assembly and manufacturability.

**Initial part breakdown (assembly, one CAD body per part):**
- base
- main body
- decorative band
- lantern (transparent)
- top cap
- internal LED module and mounting
- cable / power entry

---

## 3. Engineering rules system

Recommendations come from a structured rules layer first, with the LLM used to explain and extend.

Rule areas:
- process suitability by geometry
- common aluminium alloys and their uses
- practical sheet thickness ranges
- minimum bend radius guidance
- common machining tolerances
- casting draft requirements
- common fastening methods
- surface finish compatibility
- production-volume ranges per process
- tooling-cost categories
- manufacturing trade-offs

**Data provenance:** rules and cost data live in editable YAML/JSON seed files. Every entry carries:
- `source` (reference, or "model-generated")
- `confidence` (low / medium / high)
- `verified` (boolean, default `false`)

Unverified data is visibly flagged in the UI wherever it influences a recommendation.

**Every recommendation shows:**
- Recommendation
- Reason
- Assumptions
- Confidence
- Alternative options
- Questions that need answering

Uncertain decisions are presented as uncertain. Any recommendation that could affect product safety is explicitly flagged for human or manufacturer verification.

---

## 4. CAD

**Engine:** CadQuery (headless, pip-installable, native STEP/STL export, OCC kernel).

**Pipeline:** image → proposed dimensions/geometry → editable parameters (user confirms) → CAD. Never infer complex geometry directly from an image without confirmation.

**Eventual capabilities:** individual components, assemblies, dimensions, wall thickness, holes and fastener positions, STEP/STL/DXF export, simple 2D dimensioned drawings.

**Preview:** the CAD service also exports GLB for an in-browser viewer (react-three-fiber).

**Faro parameters (first model):**
- overall height
- body diameter
- base diameter
- wall thickness
- lantern height, lantern diameter
- top-cap dimensions
- decorative-band height
- cable-hole diameter
- mounting-hole positions

Parameters are validated (ranges, inter-dependencies such as lantern diameter ≤ body diameter, wall thickness within process limits) before regeneration.

---

## 5. Front end

Navigation:

- **Projects:** list all products.
- **Overview:** images, description, target cost, dimensions, volume.
- **Parts:** hierarchical component list. Each part: name, function, quantity, material, process, finish, dimensions, tolerances, supplier notes, cost estimate.
- **CAD:** 3D preview, parameter editor, export controls.
- **Engineering:** material and process recommendations, DFM warnings, structural / thermal / electrical considerations, open questions.
- **BOM:** editable table.
- **Manufacturing:** tooling requirements, expected MOQ, unit-cost bands, suggested factory capabilities, risks.
- **Factory Pack:** spec PDF, BOM CSV/XLSX, drawings, STEP files, assembly notes, RFQ document.

---

## 6. Factory feedback loop (later milestone)

Paste or upload manufacturer feedback. The system:
1. identifies requested changes
2. links them to parts
3. explains the likely reason for each request
4. proposes design revisions
5. lets the user accept/reject each change
6. records lessons in the knowledge base

**Manufacturing Knowledge Base:** searchable, reusable across products. Examples:
- "Supplier X cannot spin aluminium below this radius."
- "Changing wall thickness from 1.2 mm to 1.5 mm reduced rejection rate."
- "This finish showed fingerprints."

---

## 7. Compliance (later milestone)

A checklist and documentation system, kept clearly separate from accredited testing. Every item is labelled as one of:
- engineering guidance
- requirement to investigate
- certified testing / sign-off (recorded only from external evidence)

The software never states a product is legally compliant.

Areas for a UK/EU electrical lamp: electrical safety, EMC, RoHS, WEEE, product markings, technical documentation, relevant lighting standards. Scope depends on the power decision (mains vs battery).

---

## 8. Cost modelling

Inputs: material, component weight, process, labour, tooling amortisation, bought-in components, finish, packaging, quantity.

Output as ranges, e.g.:
- £32–£46 at 100 units
- £21–£30 at 500 units
- £15–£23 at 2,000 units

Show which assumptions drive cost most (sensitivity ranking). All rates come from the seed data and inherit its `verified` flag.

---

## 9. Technical architecture

- **Front end:** Vite + React + TypeScript
- **Backend:** Python (FastAPI) for API, engineering rules, cost model and CAD
- **CAD:** CadQuery
- **Database:** SQLite
- **Files:** local storage (uploads, CAD outputs, generated documents)
- **One command** starts the whole app

Clean boundaries between UI, AI reasoning, rules engine and CAD generation.

**Data model** supports, from day one: multiple projects, revisions, parts, materials/processes, versioned CAD, engineering decisions (with status: proposed / accepted / rejected / edited), suppliers, factory feedback, compliance records. Later entities may be schema-only until their milestone.

**Revisions:** an immutable snapshot of a project's requirements, parameters, parts, decisions and CAD outputs, with a note and timestamp. No branching or merging.

---

## 10. AI usage

- Provider abstraction so the model can change. Default: Anthropic API, key in `ANTHROPIC_API_KEY`.
- A mock provider for tests and for running without a key.
- The LLM returns JSON validated against defined schemas.
- Deterministic rules take priority wherever they exist.
- LLM is used for: interpreting requirements, explaining trade-offs, proposing alternatives, interpreting supplier feedback, identifying missing information, drafting documentation.
- The LLM never silently invents dimensions or specifications. Inferred values are labelled as assumptions.
- The app must remain usable with the LLM disabled.

---

## 11. UX principle

The user is not a mechanical engineer. Explain choices in plain language first, with technical detail available on demand.

Example: instead of "Use 6061-T6 CNC machined aluminium", say "Use 6061 aluminium if this part is machined. It machines cleanly, is widely available and gives a good cosmetic finish. If production volume becomes high, a cast alloy may be cheaper."

---

## 12. Milestone 1

Build a working MVP that can:

1. create/open a Faro project
2. store product requirements
3. upload reference images
4. define parts
5. recommend material/process combinations (rules engine; LLM explanation optional)
6. edit CAD parameters
7. generate a simple parametric Faro assembly
8. export STEP/STL per part and for the assembly
9. generate a BOM (CSV export)
10. generate a basic DFM report
11. save revisions

**Definition of done:**
- one command starts front end and backend
- I can create Faro, change overall height, regenerate, preview the result, and download a STEP that opens in Fusion 360 or FreeCAD
- each part has a recommendation card showing reason, assumptions, confidence, alternatives and open questions
- unverified rule data is visibly flagged
- BOM exports to CSV
- DFM report renders in the app
- saving a revision and viewing a previous one works
- the app runs with the LLM disabled
- tests pass for: engineering rules, CAD parameter validation, data models, export functions

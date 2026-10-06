"""Cost assumptions audit: every seed value behind the best configuration's unit cost,
ranked by impact, with plain-English ways to verify the top ones.

Read-only. Uses the existing sensitivity method (each input moved ±25% at the
reference quantity) and adds the seed values that are not single assumptions:
regional multipliers (moved as a group) and material densities.
"""

from __future__ import annotations

import csv
import io
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.costing.assemble import CostConfig, assemble
from app.costing.data import load_cost_data
from app.costing.model import CostInputs, evaluate, material_price, sensitivity, total
from app.models import Project
from app.rules.data import load_rules
from app.services import costdown
from app.services.costing import snapshot

AUDIT_QUANTITY = 500
STEP = 0.25
TOP_N = 15


# ---------------------------------------------------------------------------
# Where each value lives in the seed data
# ---------------------------------------------------------------------------


def _seed_location(key: str, inputs: CostInputs, ctx: dict[str, Any], items_by_id: dict[int, Any]) -> tuple[str, str]:
    """(seed file, entry) for an assumption key."""
    kind, _, rest = key.partition(":")
    if kind == "mat_price":
        return "seed/cost/material_prices.yaml", f"{rest}.gbp_per_kg"
    field = {"rate": "machine_gbp_per_hr", "setup": "setup_hours", "cycle": "cycle_min", "cycle_kg": "cycle_min_per_kg",
             "util": "material_utilisation", "removal": "min_per_cm3_removed"}.get(kind)
    if field:
        return "seed/cost/process_rates.yaml", f"{rest}.{field}"
    if kind == "finish_m2":
        return "seed/cost/finish_rates.yaml", f"{rest}.gbp_per_m2"
    if kind == "finish_min":
        return "seed/cost/finish_rates.yaml", f"{rest}.min_per_part"
    if kind == "tooling":
        spec = next((p for p in inputs.parts if str(p.part_id) == rest), None)
        return "seed/rules/tooling_cost.yaml", f"{spec.tooling_band if spec else '?'} band"
    if key == "labour_rate":
        return "seed/cost/general.yaml", "labour_gbp_per_hr"
    if key == "region_freight_duty":
        return "seed/cost/regions.yaml", f"{ctx['region'].key}.freight_duty_pct"
    if kind == "extra":
        return "seed/cost/bought_in.yaml", rest
    if kind == "item":
        it = items_by_id.get(int(rest))
        if it is not None and it.source == "user":
            return "project cost items (edited by you)", it.name
        return "seed/cost/bought_in.yaml", (it.price_key if it is not None and it.price_key else "?")
    if kind == "item_qty":
        return "seed/products/faro.yaml", "cost_items (assembly minutes)"
    if kind == "discount":
        if inputs.assumptions[key].source.startswith("user"):
            return "project cost settings (edited by you)", f"volume discount: {rest}"
        return "seed/cost/general.yaml", f"volume_discount_{rest}"
    if kind == "commodity":
        return "seed/cost/commodities.yaml", rest
    return "?", key


def _seed_span(key: str, inputs: CostInputs, rules, cost) -> tuple[float, float] | None:
    """The seed's own low/high for values the region scales (None if unscaled)."""
    kind, _, rest = key.partition(":")
    if kind == "rate" and rest in cost.process_rates:
        sp = cost.process_rates[rest].machine_gbp_per_hr
        return sp.low, sp.high
    if kind == "finish_m2" and rest in cost.finish_rates:
        sp = cost.finish_rates[rest].gbp_per_m2
        return sp.low, sp.high
    if kind == "finish_min" and rest in cost.finish_rates:
        sp = cost.finish_rates[rest].min_per_part
        return sp.low, sp.high
    if key == "labour_rate":
        v = cost.general["labour_gbp_per_hr"].value
        return v["low"], v["high"]
    if kind == "tooling":
        spec = next((p for p in inputs.parts if str(p.part_id) == rest), None)
        if spec:
            band = rules.tooling_cost[spec.tooling_band]
            return band.gbp_min, band.gbp_max
    return None


# ---------------------------------------------------------------------------
# How to verify (plain English), by kind of value
# ---------------------------------------------------------------------------


def how_to_verify(key: str, label: str, inputs: CostInputs, ctx: dict[str, Any], items_by_id: dict[int, Any]) -> str:
    kind, _, rest = key.partition(":")
    if kind == "discount":
        return ("Ask two suppliers for their price at 100, 500 and 2,000 pcs; the ratio of the 500-pc price to the "
                "small-quantity price is the real discount.")
    if kind == "commodity":
        if "conversion" in rest:
            return "Ask a sheet supplier or spinner for the price of 1050 spinning circles in £/kg and subtract the metal value."
        if "premium" in rest:
            return "Check the regional premium in a metals price report, or ask a mill for its metal surcharge basis."
        return "Published market data: check on the day you order (LME / Bank of England)."
    if kind == "mat_price":
        if rest.startswith("al_"):
            return ("Ask an aluminium stockist for a price per kg for this alloy and form (sheet discs or bar) at your quantity; "
                    "sanity-check against the LME aluminium price plus a typical sheet/bar premium.")
        if rest in ("pmma", "pc"):
            return "Ask a plastics stockist for the price of the stock tube size per metre and convert to £/kg."
        if rest == "brass":
            return "Ask a brass stockist (CZ108 sheet / CZ121 bar) for a price per kg; check against the LME copper and zinc prices."
        return "Ask a stockist for a price per kg in the form the process needs."
    if kind == "rate":
        if rest == "metal_spinning":
            return ("Send the STEP files to 2–3 spinning shops and ask for a unit price at 500 pcs; ask them to split it into "
                    "material, spinning time and trimming so the hourly rate can be back-calculated.")
        if rest == "cnc_machining":
            return "Get an online CNC quote (e.g. Xometry) at 500 pcs and ask a local shop for its hourly machine rate."
        return "Ask a supplier for their hourly machine rate, or back-calculate it from a unit-price quote."
    if kind in ("cycle", "cycle_kg"):
        return "Ask the shop how long one part takes on the machine (including loading and trimming), or time a sample run."
    if kind == "removal":
        return "A CNC quote for the part at 500 pcs captures machining time directly; compare it with this estimate."
    if kind == "util":
        return "Ask the shop what blank size they cut per part (disc or strip dimensions) and how much is trimmed off."
    if kind == "setup":
        return "Ask for the setup or first-off charge per batch, separate from the unit price."
    if kind in ("finish_m2", "finish_min"):
        return ("Get a lacquer / powder-coat shop quote per part at 500 pcs, including masking and colours, and ask for their "
                "minimum charge per part and per batch.")
    if kind == "tooling":
        spec = next((p for p in inputs.parts if str(p.part_id) == rest), None)
        if spec and spec.process_key == "metal_spinning":
            return "Ask the spinning shop what the spinning form (chuck) costs and whether it is a one-off charge."
        if spec and spec.tooling_band == "none":
            return "No tooling expected for this route; confirm the supplier doesn't charge for fixtures."
        return "Ask for the one-off tooling cost and who owns the tool."
    if key == "labour_rate":
        return "Ask your assembler or contract manufacturer for their hourly labour rate (fully loaded)."
    if kind == "item_qty":
        return "Time the assembly of a prototype (wiring, fixing, testing), or ask the assembler to quote per unit."
    if key == "region_freight_duty":
        return ("Ask a freight forwarder for a per-carton price to the UK and check the UK tariff for table lamps "
                "(commodity code 9405) for the duty rate.")
    if key.startswith("region_mult:"):
        return "Get the same part quoted in the UK and in this region; the ratio of the two prices is the real multiplier."
    if key.startswith("density:"):
        return "Physical constant from the material datasheet; low risk."
    # Bought-in items (project items or scenario/route extras)
    name = label.lower()
    if "led module" in name:
        return "Get distributor prices (e.g. Mouser, Farnell, LCSC) for the LED module at 500 pcs."
    if "driver" in name or "adapter" in name:
        return "Get a certified driver/adapter price at 500 pcs from a distributor, with its certificates for the target markets."
    if "cable" in name:
        return "Ask a cable-assembly maker to quote the cable with plug, switch and fabric braid at 500 pcs."
    if "box" in name or "packaging" in name:
        return "Ask a packaging supplier to quote the retail box and inserts at 500 pcs."
    if "weight plate" in name:
        return "Get a laser-cut steel quote for the plate (thickness, diameter, zinc plating) at 500 pcs."
    if "gasket" in name:
        return "Ask a silicone moulder or gasket supplier for a price at 500 pcs (a stock O-ring may do)."
    return "Get a distributor or supplier price at 500 pcs."


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def _group_swing(inputs: CostInputs, keys: list[str], q: float) -> tuple[float, float, float]:
    mids = inputs.mids()
    up = total(evaluate(inputs, {**mids, **{k: mids[k] * (1 + STEP) for k in keys}}, q))
    down = total(evaluate(inputs, {**mids, **{k: mids[k] * (1 - STEP) for k in keys}}, q))
    return down, up, (up - down) / 2


def _density_swing(inputs: CostInputs, material_key: str, q: float) -> tuple[float, float, float]:
    def with_factor(f: float) -> float:
        parts = [replace(p, density_g_cm3=p.density_g_cm3 * f) if p.material_key == material_key else p for p in inputs.parts]
        alt = CostInputs(assumptions=inputs.assumptions, parts=parts, items=inputs.items, spread=inputs.spread,
                         overhead_key=inputs.overhead_key)
        return total(evaluate(alt, alt.mids(), q))
    down, up = with_factor(1 - STEP), with_factor(1 + STEP)
    return down, up, (up - down) / 2


def cost_audit(session: Session, project: Project) -> dict[str, Any]:
    rules, cost = load_rules(), load_cost_data()
    snap = snapshot(session, project)
    defs = {d["key"]: d for d in costdown.scenario_defs(project)}
    q = AUDIT_QUANTITY
    if defs:
        best = costdown.optimise(snap, defs, q, rules, cost, tier="strict")
        selection, region = best["selection"], best["region"]
        cfg = costdown.selection_config(defs, selection, region, snap.params)
    else:
        selection, region, cfg = [], "uk", CostConfig()
    inputs, ctx = assemble(snap, cfg, rules, cost)
    base = total(evaluate(inputs, inputs.mids(), q))
    items_by_id = {it.item_id: it for it in snap.items}

    rows: list[dict[str, Any]] = []
    for s in sensitivity(inputs, q, STEP):
        a = inputs.assumptions[s["key"]]
        file, entry = _seed_location(s["key"], inputs, ctx, items_by_id)
        seed = _seed_span(s["key"], inputs, rules, cost) or (a.low, a.high)
        rows.append({
            "key": s["key"], "label": s["label"], "group": s["group"], "unit": a.unit,
            "low": seed[0], "high": seed[1], "value": round(a.mid, 4),
            "source": a.source, "confidence": a.confidence, "verified": a.verified,
            "seed_file": file, "seed_entry": entry,
            "cost_down": s["cost_down"], "cost_up": s["cost_up"], "swing": s["swing"], "swing_pct": s["swing_pct"],
        })

    # Regional multipliers: one seed value scales a whole group of inputs.
    r = ctx["region"]
    if r.key != "uk":
        groups = {
            "machine": [k for k in inputs.assumptions if k.startswith("rate:")],
            "labour": ["labour_rate"],
            "tooling": [k for k in inputs.assumptions if k.startswith("tooling:")],
            "finishing": [k for k in inputs.assumptions if k.startswith("finish_")],
        }
        for name, keys in groups.items():
            keys = [k for k in keys if k in inputs.assumptions]
            if not keys:
                continue
            span = getattr(r, name)
            down, up, swing = _group_swing(inputs, keys, q)
            rows.append({
                "key": f"region_mult:{name}", "label": f"{r.name} {name} cost multiplier (vs UK)", "group": "Region",
                "unit": "×", "low": span.low, "high": span.high, "value": round((span.low + span.high) / 2, 4),
                "source": r.source, "confidence": r.confidence, "verified": r.verified,
                "seed_file": "seed/cost/regions.yaml", "seed_entry": f"{r.key}.{name}",
                "cost_down": round(down, 2), "cost_up": round(up, 2), "swing": round(swing, 2),
                "swing_pct": round(swing / base * 100, 1) if base else 0.0,
            })

    # Material densities (rules data) set part weights.
    for mat_key in sorted({p.material_key for p in inputs.parts}):
        spec = next(p for p in inputs.parts if p.material_key == mat_key)
        m = rules.materials.get(mat_key)
        down, up, swing = _density_swing(inputs, mat_key, q)
        prov = m if m else cost.material_prices[mat_key]
        rows.append({
            "key": f"density:{mat_key}", "label": f"{spec.material_name} density", "group": "Material properties",
            "unit": "g/cm³", "low": spec.density_g_cm3, "high": spec.density_g_cm3, "value": spec.density_g_cm3,
            "source": prov.source, "confidence": prov.confidence, "verified": prov.verified,
            "seed_file": "seed/rules/materials.yaml" if m else "seed/cost/material_prices.yaml",
            "seed_entry": f"{mat_key}.density_g_cm3",
            "cost_down": round(down, 2), "cost_up": round(up, 2), "swing": round(swing, 2),
            "swing_pct": round(swing / base * 100, 1) if base else 0.0,
        })

    prices = price_basis_rows(inputs, cost, items_by_id)

    rows.sort(key=lambda x: -abs(x["swing"]))
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
        row["how_to_verify"] = how_to_verify(row["key"], row["label"], inputs, ctx, items_by_id) if i <= TOP_N else ""

    return {
        "project": project.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quantity": q,
        "step": STEP,
        "configuration": {
            "label": "Best with no compromise to look and feel",
            "changes": costdown.describe_selection(defs, selection) if defs else [],
            "region": region, "region_name": cost.regions[region].name,
        },
        "unit_cost_mid": round(base, 2),
        "unit_cost_raw_mid": round(total(evaluate(inputs, inputs.mids(), q, raw=True)), 2),
        "rows": rows,
        "prices": prices,
        "unverified": sum(1 for x in rows if not x["verified"]),
        "notes": [
            f"Impact: each value moved ±{STEP:.0%} with everything else at its midpoint, at {q} units "
            "(the Manufacturing tab's sensitivity method). Regional multipliers move all the inputs they scale together.",
            "'Seed value' is the seed file's own low–high. 'Used' is the midpoint the model uses in this configuration, "
            "after the region scales machine, labour, tooling and finishing values.",
            "Densities are physical constants from material datasheets: they rank high because part weight drives material and "
            "spinning time, but they are low-risk and not a verification priority.",
            "Range widening for confidence affects the range only, not the midpoint, so it is not listed.",
        ],
    }


BASIS_LABEL = {"trade_volume": "trade / volume", "distributor_small_qty": "distributor, small quantity",
               "retail": "retail", "model_estimate": "model estimate"}


def price_basis_rows(inputs: CostInputs, cost, items_by_id: dict[int, Any]) -> list[dict[str, Any]]:
    """Each price input: researched (raw) price and basis next to the volume-adjusted price at 500 and 2,000."""
    mids = inputs.mids()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in inputs.parts:
        k = inputs.keys_for_part(p)
        if k["price"] in seen:
            continue
        seen.add(k["price"])
        a = inputs.assumptions[k["price"]]
        mp = cost.material_prices.get(p.material_key)
        adj = {str(q): round(material_price(p, k, mids, q)[0], 2) for q in (500, 2000)}
        out.append({
            "label": a.label, "unit": "£/kg", "raw_low": a.low, "raw_high": a.high, "raw_mid": round(a.mid, 4),
            "basis": BASIS_LABEL.get(mp.price_basis if mp else "model_estimate", "?"),
            "basis_quantity": mp.basis_quantity if mp else None,
            "adjustment": ("trade basis (LME + premium + sheet conversion)" if p.trade_keys else
                           ("volume discount" if p.price_discount_key else "none")),
            "adjusted": adj, "source": a.source,
        })
    for it in inputs.items:
        if it.unit != "pcs" or it.cost_key in seen:
            continue
        seen.add(it.cost_key)
        a = inputs.assumptions[it.cost_key]
        if it.cost_key.startswith("extra:"):
            bp = cost.bought_in[it.cost_key.split(":", 1)[1]]
            basis, bq = bp.price_basis, bp.basis_quantity
        else:
            db = items_by_id.get(it.item_id)
            basis, bq = (db.price_basis, db.basis_quantity) if db is not None else ("model_estimate", None)
        disc = mids.get(it.discount_key, 1.0) if it.discount_key else 1.0
        adj = {str(q): round(a.mid * (disc if it.discount_key and q >= it.discount_from else 1.0), 2) for q in (500, 2000)}
        out.append({
            "label": a.label, "unit": "£", "raw_low": a.low, "raw_high": a.high, "raw_mid": round(a.mid, 4),
            "basis": BASIS_LABEL.get(basis, basis), "basis_quantity": bq,
            "adjustment": "volume discount" if it.discount_key else "none",
            "adjusted": adj, "source": a.source,
        })
    return out


def _fmt_value(row: dict[str, Any]) -> str:
    lo, hi, unit = row["low"], row["high"], row["unit"]
    num = (lambda v: f"{v:g}")
    if unit.startswith("£"):
        val = f"£{num(lo)}" if lo == hi else f"£{num(lo)}–£{num(hi)}"
        return val + unit[1:]
    val = num(lo) if lo == hi else f"{num(lo)}–{num(hi)}"
    return f"{val} {unit}".strip()


def _fmt_used(row: dict[str, Any]) -> str:
    v, unit = row["value"], row["unit"]
    if unit.startswith("£"):
        return f"£{v:,.4g}{unit[1:]}"
    return f"{v:,.4g} {unit}".strip()


def audit_markdown(a: dict[str, Any]) -> str:
    cfg = a["configuration"]
    changes = ", ".join(f"{c['letter']}. {c['label']}" + (f" ({c['option_label']})" if c["option_label"] else "")
                        for c in cfg["changes"]) or "no design changes"
    lines = [
        f"# Cost assumptions audit: {a['project']}",
        "",
        f"Generated {a['generated_at'][:16].replace('T', ' ')} UTC by Product Workbench.",
        "",
        f"**Configuration:** {cfg['label']}: {changes}; made in {cfg['region_name']}.  ",
        f"**Unit cost (midpoint) at {a['quantity']} units:** £{a['unit_cost_mid']:.2f}.  ",
        f"**Values feeding it:** {len(a['rows'])}, of which {a['unverified']} are unverified.",
        "",
        "> Every value below is a model-generated assumption unless its source says otherwise. "
        "Verify the top of the list first: it moves the unit cost most.",
        "",
        "| # | Assumption | Seed file → entry | Seed value | Used | Source | Confidence | Verified | Impact ±25% | How to verify |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in a["rows"]:
        lines.append(
            f"| {r['rank']} | {r['label']} | `{r['seed_file']}` → `{r['seed_entry']}` | {_fmt_value(r)} | "
            f"{_fmt_used(r)} | {r['source']} | "
            f"{r['confidence']} | {'yes' if r['verified'] else 'no'} | ±£{abs(r['swing']):.2f} ({abs(r['swing_pct']):.1f}%) | "
            f"{r['how_to_verify']} |"
        )
    lines += [
        "",
        "## Researched prices vs volume-adjusted prices",
        "",
        f"Unit cost at {a['quantity']} with every price at its researched basis (no volume adjustment): "
        f"£{a['unit_cost_raw_mid']:.2f}; volume-adjusted: £{a['unit_cost_mid']:.2f}.",
        "",
        "| Price | Researched (raw) | Basis | Basis qty | Adjustment | Used at 500 | Used at 2,000 |",
        "|---|---|---|---|---|---|---|",
    ]
    for pr in a.get("prices", []):
        raw = f"£{pr['raw_low']:g}" if pr["raw_low"] == pr["raw_high"] else f"£{pr['raw_low']:g}–£{pr['raw_high']:g}"
        unit = "/kg" if pr["unit"] == "£/kg" else ""
        bq = f"{pr['basis_quantity']:g}" if pr["basis_quantity"] else "—"
        lines.append(f"| {pr['label']} | {raw}{unit} | {pr['basis']} | {bq} | {pr['adjustment']} | "
                     f"£{pr['adjusted']['500']:.2f}{unit} | £{pr['adjusted']['2000']:.2f}{unit} |")
    lines += ["", "## Notes", ""] + [f"- {n}" for n in a["notes"]]
    return "\n".join(lines) + "\n"


def audit_csv(a: dict[str, Any]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Rank", "Assumption", "Group", "Seed file", "Seed entry", "Used (midpoint)", "Seed low", "Seed high", "Unit", "Source",
                "Confidence", "Verified", "Impact ±25% (GBP)", "Impact ±25% (%)", "How to verify"])
    for r in a["rows"]:
        w.writerow([r["rank"], r["label"], r["group"], r["seed_file"], r["seed_entry"], r["value"], r["low"], r["high"],
                    r["unit"], r["source"], r["confidence"], "yes" if r["verified"] else "no", abs(r["swing"]),
                    abs(r["swing_pct"]), r["how_to_verify"]])
    return buf.getvalue()

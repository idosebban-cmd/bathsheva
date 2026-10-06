"""Bill of materials from parts, latest CAD and joints."""

from __future__ import annotations

import csv
import io
from typing import Any

from app.models import Project
from app.services.cad import current_parameters, latest_model
from app.services.recommendations import project_recommendations
from app.services.templates import load_template

CSV_COLUMNS = [
    ("item", "Item"),
    ("level", "Level"),
    ("name", "Part"),
    ("quantity", "Qty"),
    ("material", "Material"),
    ("process", "Process"),
    ("finish", "Finish"),
    ("size_mm", "Size (mm)"),
    ("status", "Status"),
    ("cost_low", "Unit cost low (GBP)"),
    ("cost_high", "Unit cost high (GBP)"),
    ("supplier_notes", "Supplier notes"),
    ("flags", "Flags"),
]


def _tree(parts):
    ids = {p.id for p in parts}
    children: dict[int | None, list] = {}
    for p in parts:
        key = p.parent_id if p.parent_id in ids else None
        children.setdefault(key, []).append(p)
    out = []

    def walk(parent, depth):
        for p in sorted(children.get(parent, []), key=lambda x: x.sort_order):
            out.append((p, depth))
            walk(p.id, depth + 1)

    walk(None, 0)
    return out


def _hardware(project: Project, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Hardware lines listed on the template's joints. Quantities and sizes are assumptions."""
    if not project.template:
        return []
    rows = []
    for j in load_template(project.template).get("joints", []):
        for h in j.get("hardware", []):
            rows.append({"name": h["name"], "quantity": h.get("quantity", 1), "material": h.get("material", ""),
                         "notes": h.get("notes", ""), "assumption": True, "safety": bool(h.get("safety"))})
    return rows


def _cad_keys(project: Project) -> list[str]:
    return [p.cad_key for p in project.parts if p.cad_key]


# Route extras that are modelled as their own CAD part (so the BOM doesn't list them twice).
EXTRA_AS_PART = {"steel_weight_plate": "weight_plate"}


def _route_extras(project: Project) -> list[dict[str, Any]]:
    """Extra parts the chosen process routes need (e.g. a weight plate for a spun base)."""
    from sqlalchemy.orm import object_session

    from app.services.costing import build_inputs

    session = object_session(project)
    if session is None or not project.template:
        return []
    inputs, ctx = build_inputs(session, project)
    out = []
    keys = set(_cad_keys(project))
    for it in inputs.items:
        if it.part_id is None:
            continue
        ex = ctx["extras"][it.item_id]
        if EXTRA_AS_PART.get(ex.price_key) in keys:
            continue
        origin = ex.origin
        out.append({"name": it.name, "quantity": it.quantity, "origin": origin})
    return out


def build_bom(project: Project) -> dict[str, Any]:
    recs = {r["part_id"]: r for r in project_recommendations(project)}
    latest = latest_model(project)
    info = latest.part_info if latest else {}
    params = current_parameters(project) if project.template else {}

    rows: list[dict[str, Any]] = []
    n = 0
    for part, depth in _tree(project.parts):
        n += 1
        rec = recs.get(part.id) or {}
        r = rec.get("recommendation") or {}
        decided = bool(part.material or part.process)
        size = info.get(part.cad_key or "", {}).get("size_mm")
        flags = []
        if not decided and rec.get("uses_unverified_data"):
            flags.append("unverified rule data")
        if rec.get("safety_flags"):
            flags.append("safety: verify")
        if part.cost_low is None or part.cost_high is None:
            flags.append("cost TBD")
        rows.append({
            "item": str(n),
            "level": depth,
            "part_id": part.id,
            "cad_key": part.cad_key,
            "name": part.name,
            "quantity": part.quantity,
            "material": part.material or r.get("material_name", ""),
            "process": part.process or r.get("process_name", ""),
            "finish": part.finish,
            "size_mm": " x ".join(f"{v:.1f}" for v in size) if size else "",
            "status": "decided" if decided else ("recommended" if r else "TBD"),
            "cost_low": part.cost_low,
            "cost_high": part.cost_high,
            "supplier_notes": part.supplier_notes,
            "flags": flags,
            "derived": False,
        })

    from app.services.costdown import cad_mismatches

    mismatched = {m["part_id"]: m for m in cad_mismatches(project)}
    for row in rows:
        if row["part_id"] in mismatched:
            row["flags"].append("CAD mismatch")
            row["supplier_notes"] = (row["supplier_notes"] + " " if row["supplier_notes"] else "") + (
                "CAD not yet updated for the chosen route: " + " ".join(mismatched[row["part_id"]]["changes"]))
    for i, ex in enumerate(_route_extras(project), start=1):
        rows.append({
            "item": f"R{i}", "level": 0, "part_id": None, "cad_key": None, "name": ex["name"], "quantity": ex["quantity"],
            "material": "", "process": "Bought-in", "finish": "", "size_mm": "", "status": "derived",
            "cost_low": None, "cost_high": None, "supplier_notes": f"Needed by the {ex['origin']}.",
            "flags": ["assumption", "cost TBD"], "derived": True,
        })

    hw = _hardware(project, params)
    for i, h in enumerate(hw, start=1):
        rows.append({
            "item": f"H{i}",
            "level": 0,
            "part_id": None,
            "cad_key": None,
            "name": h["name"],
            "quantity": h["quantity"],
            "material": h["material"],
            "process": "Bought-in",
            "finish": "",
            "size_mm": "",
            "status": "derived",
            "cost_low": None,
            "cost_high": None,
            "supplier_notes": h["notes"],
            "flags": (["assumption"] if h.get("assumption") else []) + (["safety: verify"] if h.get("safety") else []) + ["cost TBD"],
            "derived": True,
        })

    priced = [r for r in rows if r["cost_low"] is not None and r["cost_high"] is not None]
    total = {
        "low": round(sum(r["cost_low"] * r["quantity"] for r in priced), 2),
        "high": round(sum(r["cost_high"] * r["quantity"] for r in priced), 2),
        "priced_items": len(priced),
        "total_items": len(rows),
        "complete": len(priced) == len(rows),
    }
    return {
        "rows": rows,
        "total": total,
        "cad_version": latest.version if latest else None,
        "notes": [
            "Material/process show your decision where set, otherwise the rules-engine recommendation (status 'recommended').",
            "Hardware lines (H…) are derived from the joint design; quantities and sizes are assumptions.",
            "Sizes come from the latest generated CAD (bounding box)." if latest else "Generate CAD to fill in part sizes.",
        ],
    }


def bom_csv(project: Project) -> str:
    bom = build_bom(project)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([label for _, label in CSV_COLUMNS])
    for row in bom["rows"]:
        out = []
        for key, _ in CSV_COLUMNS:
            v = row[key]
            if key == "name":
                v = "  " * row["level"] + v
            elif key == "flags":
                v = "; ".join(v)
            elif v is None:
                v = "TBD" if key.startswith("cost") else ""
            out.append(v)
        w.writerow(out)
    t = bom["total"]
    w.writerow([])
    w.writerow(["", "", "Total (priced items only)" if not t["complete"] else "Total", "", "", "", "", "", "",
                t["low"], t["high"], f"{t['priced_items']}/{t['total_items']} items priced", ""])
    return buf.getvalue()

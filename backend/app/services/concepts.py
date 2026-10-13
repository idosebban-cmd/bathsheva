"""Standard parts library and product concepts: payloads for the Standard Parts page, and saved concepts."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app import standard_parts as sp
from app.costing.data import load_cost_data
from app.models import Concept


class UnknownParts(ValueError):
    def __init__(self, ids: list[str]):
        super().__init__(f"Unknown library parts: {', '.join(ids)}")
        self.ids = ids


def pricing() -> dict[str, float]:
    """VAT and the DTC factory share from seed/cost/pricing.yaml (the same defaults as the Cost-down tab)."""
    p = load_cost_data().pricing
    return {"vat_rate": p["vat_rate"].value, "dtc_factory_share": p["dtc_factory_share"].value}


def cost(lines: list[dict[str, Any]], retail_price: float | None,
         library: sp.Library | None = None) -> dict[str, Any]:
    lib = library or sp.load_library()
    p = pricing()
    return sp.cost_lines(lines, lib.parts, retail_price, p["vat_rate"], p["dtc_factory_share"])


def library_payload() -> dict[str, Any]:
    lib = sp.load_library()
    return {
        "sections": [
            {"number": s.number, "title": s.title,
             "subsections": [{"number": sub.number, "title": sub.title, "notes": sub.notes,
                              "parts": [part.to_dict() for part in sub.parts]} for sub in s.subsections]}
            for s in lib.sections
        ],
        "about": lib.about,
        "aliases": lib.aliases,
        "fx": sp.FX,
        "quantities": list(sp.QUANTITIES),
        "room_share": sp.ROOM,
        "pricing": pricing(),
    }


def seed_concepts() -> list[dict[str, Any]]:
    lib = sp.load_library()
    return [{**c.to_dict(), "cost": cost(c.lines, c.retail_price, lib)} for c in sp.load_concepts()]


def _clean_lines(lines: list[dict[str, Any]], library: sp.Library) -> list[dict[str, Any]]:
    unknown = sorted({ln["part_id"] for ln in lines if ln["part_id"] not in library.parts})
    if unknown:
        raise UnknownParts(unknown)
    out = []
    for ln in lines:
        # Saved under the part's current id, so a renamed part's old id is replaced on the next save.
        row = {"part_id": library.current_id(ln["part_id"]), "quantity": float(ln.get("quantity") or 0),
               "note": ln.get("note", ""),
               "option": int(ln.get("option") or 0)}
        row.update({k: float(ln[k]) for k in sp.DIM_KEYS if ln.get(k) is not None})
        if ln.get("view"):
            row["view"] = dict(ln["view"])  # the 3D view's placement (validated by the API)
        # Store the fraction the sizes come to as well, so the line still reads sensibly without them.
        if any(k in row for k in ("length_mm", "width_mm", "height_mm")):
            part = library.parts[row["part_id"]]
            qty, mode, _ = sp.line_quantity(row, part, row["option"])
            if mode != "units":
                row["quantity"] = round(qty, 6)
        out.append(row)
    return out


def concept_out(row: Concept, library: sp.Library | None = None) -> dict[str, Any]:
    return {
        "id": row.id, "name": row.name, "retail_price": row.retail_price, "based_on": row.based_on,
        "lines": row.lines, "notes": row.notes, "created_at": row.created_at, "updated_at": row.updated_at,
        "cost": cost(row.lines, row.retail_price, library),
    }


def list_concepts(session: Session) -> list[dict[str, Any]]:
    lib = sp.load_library()
    return [concept_out(r, lib) for r in session.query(Concept).order_by(Concept.updated_at.desc(), Concept.id.desc())]


def save_concept(session: Session, data: dict[str, Any], row: Concept | None = None) -> Concept:
    """Create (row None) or replace a concept. Raises UnknownParts for part ids not in the library."""
    lib = sp.load_library()
    lines = _clean_lines(data.get("lines", []), lib)
    if row is None:
        row = Concept()
        session.add(row)
    row.name = data["name"]
    row.retail_price = data.get("retail_price")
    row.based_on = data.get("based_on")
    row.lines = lines
    row.notes = data.get("notes", "")
    session.commit()
    return row

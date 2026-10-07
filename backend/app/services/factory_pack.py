"""Factory Pack (SPEC §5), first part: the RFQ pack.

Builds 2D quotation drawings (SVG + PDF) for each made-to-drawing part, an RFQ
document (Markdown + PDF) and one zip with drawings, STEP files, the RFQ and the
BOM CSV. Read-only: nothing here changes the project.

Our own cost estimates and targets are deliberately left out of everything sent
to suppliers.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.cad import faro
from app.config import settings
from app.costing.data import load_cost_data
from app.factory import drawings as dr
from app.factory import logo, nameplate
from app.models import Project
from app.products import product_for
from app.rules.data import load_rules
from app.services.bom import bom_csv, build_bom
from app.services.cad import current_parameters, latest_model, mass_estimate
from app.services.recommendations import project_recommendations
from app.services.templates import load_template

QUANTITY_TIERS = [300, 500, 2000]

# Cost items that are drawn parts (listed with the drawings) or duplicates of the joint hardware
# the BOM already lists; operations are priced into the part they are done on.
DRAWN_ITEM_KEYS = {"steel_weight_plate", "bottom_plate"}
HARDWARE_ITEM_KEYS = {"screw_m25_cs", "standoff_m25", "screw_m3", "magnet_6x2", "silicone_gasket"}
OPERATION_ITEM_KEYS = {"window_laser_cut": "tower", "masked_stripe": "tower", "knob_logo_engrave": "knob", "knob_knurl": "knob"}
# What the RFQ says for these operations, whatever name a project's (possibly older) cost item carries.
OPERATION_TEXT = {"masked_stripe": "Masked two-tone lacquer: red lower section with a crisp, level line",
                  "knob_logo_engrave": "Engrave the logo on the knob face (laser or CNC, 0.2 mm deep): no fill, tone-on-tone, "
                                       "groove floor left matte; before the clear lacquer",
                  "knob_knurl": "Fine straight knurl on the knob edge (DIN 82 RAA 0.5), on the lathe"}
ELECTRONIC_PARTS = {"led_module", "tower_light", "battery", "charge_board", "dimmer"}

# How to quote each brass part on a near-net basis (quote B), next to the supplier's preferred method.
NEAR_NET_BASIS = {
    "gallery": "Spun from a 1.0 mm CZ108 brass disc; locating ring turned from brass tube",
    "lantern_frame": "Bottom ring and top band turned from brass tube; mullions from drawn brass flat",
    "cap_spigot": "Turned from brass tube close to the finished OD and bore",
    "finial": "Turned from close-fitting brass bar (just over the ball diameter)",
    "knob": "Turned from close-fitting brass bar (just over the knob diameter)",
    "railing": "Photo-etched from 0.6 mm brass sheet, rolled and soldered (already near-net)",
    "nameplate": "Photo-etched from 0.8 mm brass sheet, formed to the base radius (already near-net)",
}

SAFETY_SHORT = {
    "stability": "tip-over stability to be tested on the finished lamp",
    "glass_breakage": "glass breakage, edge finishing and retention to be verified",
    "exposed_metal_mains": "exposed metal on a mains lamp: earthing (Class I) or double insulation (Class II) to be decided",
    "electrical_component": "certified component; electrical safety to be verified by a test lab",
    "cable_anchorage": "cable anchorage / strain relief is safety-critical; verify by test",
    "battery": "Li-ion battery safety: protection circuit, UN38.3 and IEC 62133-2 to be verified",
    "polymer_near_heat": "plastic near the LED: thermal check",
    "sharp_edges": "sharp edges must be removed",
}


class FactoryPackError(ValueError):
    pass


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "part"


# ---------------------------------------------------------------------------
# Content model
# ---------------------------------------------------------------------------


@dataclass
class Block:
    kind: str  # h1 | h2 | p | bullets | table | warn
    text: str = ""
    items: list[str] | None = None
    header: list[str] | None = None
    rows: list[list[str]] | None = None
    widths: list[float] | None = None  # relative column widths for the PDF


def _drawn_parts(project: Project) -> list[str]:
    tpl = load_template(project.template) if project.template else {}
    keys = {p.cad_key for p in project.parts if p.cad_key}
    extra = {p["cad_key"] for p in tpl.get("parts", []) if p.get("made_to_drawing")}
    return [k for k in dr.DRAWN_PARTS if k in keys or k in extra]


def pack_contents(project: Project) -> dict[str, Any]:
    """Everything the pack needs, gathered once (also served to the Factory Pack tab)."""
    product = product_for(project)
    if product is None or not product.factory_pack:
        raise FactoryPackError("The Factory Pack needs a parametric product (template project such as Faro).")
    params = current_parameters(project)
    bom = build_bom(project)
    recs = {r["part_id"]: r for r in project_recommendations(project)}
    rules = load_rules()
    cost = load_cost_data()
    latest = latest_model(project)
    by_key = {r["cad_key"]: r for r in bom["rows"] if r.get("cad_key")}
    assumed = set(project.assumed_fields or [])
    drawn = _drawn_parts(project)

    parts = []
    for key in drawn:
        row = by_key.get(key)
        if row is None:
            continue
        rec = recs.get(row["part_id"], {})
        unverified = []
        if "approx_dimensions" in assumed:
            unverified.append("overall size is a design placeholder (dimensions TBD)")
        if row["status"] != "decided":
            unverified.append("material and process are the workbench's recommendation, not a decision")
        proc_key = (rec.get("recommendation") or {}).get("process_key")
        for pk, proc in rules.processes.items():
            if proc.name == row["process"]:
                proc_key = pk
        proc = rules.processes.get(proc_key or "")
        if proc and proc.wall_mm and not proc.verified:
            unverified.append(f"wall thickness limits for {proc.name.lower()} come from unverified rule data")
        safety = [SAFETY_SHORT.get(f["key"], f["message"]) for f in rec.get("safety_flags", [])
                  if f["key"] not in ("polymer_near_heat",)]
        if key in ("weight_plate", "base"):
            safety = [SAFETY_SHORT["stability"]]
        parts.append({
            "cad_key": key, "part_no": f"F-{int(row['item']):02d}", "name": row["name"], "quantity": row["quantity"],
            "material": row["material"], "process": row["process"], "finish": row["finish"], "size_mm": row["size_mm"],
            "status": row["status"], "unverified": unverified, "safety": safety,
            "drawing": f"drawings/F-{int(row['item']):02d}_{_slug(row['name'])}",
            "step": f"step/F-{int(row['item']):02d}_{_slug(row['name'])}.step",
        })

    parts.sort(key=lambda pt: pt["part_no"])
    bought = _bought_in_lines(project, cost)
    hardware = [{"item": r["item"], "name": r["name"], "quantity": r["quantity"], "material": r["material"],
                 "notes": r["supplier_notes"]} for r in bom["rows"] if str(r["item"]).startswith(("H", "R"))]

    flags = []
    for row in bom["rows"]:
        rec = recs.get(row.get("part_id"), {})
        for f in rec.get("safety_flags", []):
            if f["key"] in ("polymer_near_heat",):
                continue
            flags.append({"part": row["name"], "kind": "safety", "text": SAFETY_SHORT.get(f["key"], f["message"])})
    mass = mass_estimate(project)
    from app.services.electrical import project_runtime

    runtime = project_runtime(project)
    return {
        "project": project, "params": params, "bom": bom, "parts": parts, "bought_in": bought, "hardware": hardware,
        "cad_version": latest.version if latest else None, "flags": flags, "mass": mass,
        "assumed": sorted(assumed), "date": date.today().isoformat(), "runtime": runtime,
    }


def _bought_in_lines(project: Project, cost) -> list[dict[str, Any]]:
    """Bought-in components and operations (project cost items plus route extras), without our prices.

    group: electronics (separate RFQ) | operation (priced into the part it is done on) | hardware.
    One-off costs (e.g. certification testing) and packaging are ours, not supplier components.
    """
    from sqlalchemy.orm import object_session

    from app.services.costing import build_inputs

    session = object_session(project)
    out: list[dict[str, Any]] = []
    if session is None:
        return out
    inputs, ctx = build_inputs(session, project)
    keys = {it.item_id: it.price_key for it in ctx["db_items"]}
    for it in inputs.items:
        if it.unit != "pcs" or it.kind in ("packaging", "one_off", "assembly"):
            continue
        extra = ctx["extras"].get(it.item_id)
        price_key = extra.price_key if extra is not None else keys.get(it.item_id)
        if price_key in DRAWN_ITEM_KEYS or price_key in HARDWARE_ITEM_KEYS:
            continue
        electronics = any(w in it.name.lower() for w in ("led", "driver", "adapter", "dimmer", "cable", "battery",
                                                         "board", "potentiometer", "usb"))
        group = ("electronics" if electronics else
                 "operation" if price_key in OPERATION_ITEM_KEYS or it.kind == "finishing" else "hardware")
        out.append({"name": OPERATION_TEXT.get(price_key or "", it.name), "quantity": it.quantity, "electronics": electronics, "group": group,
                    "price_key": price_key, "on_part": OPERATION_ITEM_KEYS.get(price_key or "")})
    return out


# ---------------------------------------------------------------------------
# RFQ document
# ---------------------------------------------------------------------------


def _rfq_settings(project: Project) -> dict[str, Any]:
    return (load_template(project.template).get("rfq") or {}) if project.template else {}


# Contact and commercial fields saved on the project (Factory Pack tab), with the placeholder shown when blank.
CONTACT_FIELDS: list[tuple[str, str, str]] = [
    ("company_name", "Company name", "[COMPANY NAME]"),
    ("contact_name", "Contact name and role", "[CONTACT NAME, ROLE]"),
    ("email", "Email", "[EMAIL]"),
    ("phone", "Phone", "[PHONE]"),
    ("company_address", "Company address", "[COMPANY ADDRESS]"),
    ("quote_deadline", "Quote deadline", "[QUOTE DEADLINE]"),
    ("delivery_address", "Delivery address (for DDP)", "[DELIVERY ADDRESS, to be filled in]"),
]


def contact(project: Project) -> dict[str, str]:
    saved = project.rfq_contact or {}
    return {k: " ".join(str(saved.get(k) or "").split()) for k, _, _ in CONTACT_FIELDS}


def missing_contact(project: Project) -> list[str]:
    values = contact(project)
    return [label for k, label, _ in CONTACT_FIELDS if not values[k]]


def update_contact(project: Project, changes: dict[str, Any]) -> dict[str, str]:
    unknown = set(changes) - {k for k, _, _ in CONTACT_FIELDS}
    if unknown:
        raise FactoryPackError(f"Unknown contact fields: {sorted(unknown)}")
    new = {**contact(project), **{k: " ".join(str(v or "").split()) for k, v in changes.items()}}
    for k, v in new.items():
        if len(v) > 300:
            raise FactoryPackError(f"{k} is too long (300 characters at most)")
    if new["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", new["email"]):
        raise FactoryPackError("That email address doesn't look right")
    project.rfq_contact = new
    return new


def _fill(project: Project, key: str) -> str:
    value = contact(project)[key]
    return value or next(ph for k, _, ph in CONTACT_FIELDS if k == key)


def _numbered(blocks: list[Block]) -> list[Block]:
    """Number the section headings 1, 2, 3... in order."""
    n = 0
    for blk in blocks:
        if blk.kind == "h2":
            n += 1
            blk.text = f"{n}. " + re.sub(r"^\d+\.\s*", "", blk.text)
    return blocks


def _header(c: dict[str, Any], title: str) -> list[Block]:
    """Title, our contact details (placeholders to fill in before sending) and the document line."""
    project: Project = c["project"]
    cad = f"v{c['cad_version']}" if c["cad_version"] else "(not generated)"
    return [
        Block("h1", title),
        Block("table", widths=[1.6, 6.4], header=["From", _fill(project, "company_name")], rows=[
            ["Contact", _fill(project, "contact_name")], ["Email", _fill(project, "email")], ["Phone", _fill(project, "phone")],
            ["Address", _fill(project, "company_address")], ["Quote deadline", _fill(project, "quote_deadline")],
            ["Reference", f"{project.name.upper()}-RFQ, CAD {cad}, {c['date']}"],
        ]),
        Block("p", f"{project.name} table lamp · CAD version {cad} · units: millimetres"),
    ]


def _part_names(c: dict[str, Any], keys: list[str]) -> list[str]:
    by_key = {pt["cad_key"]: pt for pt in c["parts"]}
    return [f"{by_key[k]['part_no']} {by_key[k]['name']}" for k in keys if k in by_key]


def _ral_text(col: dict[str, Any]) -> str:
    rals = col.get("ral") or []
    return " / ".join(f"{r} (approx.)" for r in rals) if rals else "n/a (natural metal)"


def _colour_refs(c: dict[str, Any]) -> dict[str, tuple[str, str]]:
    """cad_key -> (colour reference: name, hex, approximate RALs; gloss) for the supplier BOM."""
    out: dict[str, list[tuple[str, str]]] = {}
    for col in _rfq_settings(c["project"]).get("colours", []):
        ral = f", {_ral_text(col)}" if col.get("ral") else ""
        for k in col["parts"]:
            out.setdefault(k, []).append((f"{col['name']} {col['hex']}{ral}", col["gloss"]))
    return {k: (" + ".join(x[0] for x in v), " + ".join(x[1] for x in v)) for k, v in out.items()}


def _commercial(c: dict[str, Any]) -> list[Block]:
    r = _rfq_settings(c["project"])
    terms = [t.replace("[DELIVERY ADDRESS, to be filled in]", _fill(c["project"], "delivery_address"))
             for t in (r.get("incoterms") or ["FOB (port of loading)", "DDP to our UK address: [DELIVERY ADDRESS, to be filled in]"])]
    cur = " or ".join(r.get("currencies") or ["GBP"])
    return [
        Block("h2", "Commercial terms"),
        Block("bullets", items=[
            "Please quote both: " + "; and ".join(terms) + ".",
            f"Currency: {cur}. State which, and keep it the same across the quote.",
            "Prices valid for at least 90 days; state payment terms and any tooling deposit.",
        ]),
    ]


def rfq_blocks(c: dict[str, Any]) -> list[Block]:
    project: Project = c["project"]
    p = c["params"]
    mass = c["mass"] or {}
    target_mass = p.get("target_mass_kg")
    r = _rfq_settings(project)
    b: list[Block] = _header(c, f"Request for quotation: {project.name} table lamp (metalwork, glass and finishing)")
    b.append(Block("warn", "Values marked UNVERIFIED are design placeholders or unverified data. Items marked SAFETY or "
                           "COMPLIANCE must be verified with a qualified engineer or accredited test lab before production."))

    b.append(Block("h2", "1. Product summary"))
    b.append(Block("p", " ".join(project.description.split())))
    d = faro.derived({k: float(v) for k, v in p.items()})
    rt = c.get("runtime") or {}
    b.append(Block("bullets", items=[
        f"Overall height {p['overall_height']:g} mm (plus a {abs(d['felt_bottom_z']):g} mm felt pad), base Ø{p['base_diameter']:g} mm, "
        f"tower Ø{p['tower_bottom_diameter']:g}→{p['tower_top_diameter']:g} mm, lantern Ø{p['lantern_diameter']:g} mm. "
        "Form and proportions follow our approved prototype.",
        "Base: spun aluminium shell, satin black (30–50 GU), with a laser-cut steel weight plate round the battery; aluminium bottom "
        "plate on four M2.5 screws so the user can replace the battery; felt pad on magnets.",
        "Cream band: turned aluminium ring; the base screws into it (three M3) and the tower is bonded on its spigot.",
        f"Tower: spun aluminium cone, two-tone lacquer (red lower section, masked line), {int(p['window_count'])} arched windows "
        "laser-cut after spinning, an opal borosilicate diffuser tube (window zone only) and a tower light behind them.",
        "Gallery and railing: spun brass shell with a soldered turned locating ring; photo-etched brass railing rolled into a ring (please also quote "
        "soldered brass wire and lost-wax casting).",
        "Lantern: frosted borosilicate tube inside a brass frame (rings turned from tube, soldered mullions); the red spun cap "
        "twist-locks onto the frame with a turned brass bayonet spigot (four lugs, 20° turn) and a brass ball finial.",
        "Construction: bonded and screwed, no central rod; no visible fixings.",
        "Cordless: 2 x 18650 Li-ion pack, USB-C charging, rotary dimmer with a solid brass knob on the tower. The "
        "electronics are quoted separately by electronics suppliers.",
        f"Target total lamp mass {target_mass:g} kg (estimate from CAD {mass.get('total_kg', 0):.2f} kg; UNVERIFIED)."
        if target_mass else "Target mass: to be agreed.",
    ]))
    b.append(Block("p", "Where production departs from the 3D-printed prototype:"))
    b.append(Block("table", widths=[1.4, 2.6, 4.0], header=["Feature", "Prototype", "Production (please confirm or propose better)"],
                   rows=[[x["feature"], x["prototype"], x["production"]] for x in faro.PRODUCTION_CHANGES]))

    b.append(Block("h2", "2. Design constraint: visible metal must be solid metal"))
    b.append(Block("warn", "Every visible or touchable part must be solid metal (or glass for the lantern). No plastic, "
                           "metallised plastic or metal-effect paint on plastic, at any volume. Brass details are solid "
                           "brass or real plating on the metal part; no brass-look coatings. Hidden functional parts "
                           "(gaskets, grommets, insulators, strain relief) may be plastic or rubber."))

    if r.get("colours"):
        b.append(Block("h2", "Colours and finishes"))
        b.append(Block("warn", r.get("colour_note", "Physical colour samples will be supplied.")))
        b.append(Block("table", widths=[1.7, 2.5, 0.9, 2.2, 2.1],
                       header=["Finish", "Parts", "Hex (design reference)", "Nearest RAL (approximate)", "Gloss"],
                       rows=[[col["name"], ", ".join(_part_names(c, col["parts"])), col["hex"], _ral_text(col), col["gloss"]]
                             for col in r["colours"]]))
        b.append(Block("p", "The tower is two-tone: oxblood red from the foot to the masked line, cream above it. Gloss is measured "
                            "at 60° on the finished part. All visible brass is brushed to an even satin grain (matching our Atelier "
                            "speaker) and clear-lacquered; brass is natural metal, so its hex is a reference only, never a paint "
                            "colour. Keep the brush direction consistent between parts (horizontal as fitted)."))

    b.append(Block("h2", "Quantities"))
    b.append(Block("p", "Please quote each of these order quantities: " + ", ".join(f"{q:,}" for q in QUANTITY_TIERS)
                        + " lamps (one order of each size, not cumulative). Tell us your MOQ if it is above any of them."))
    if r.get("first_order"):
        b.append(Block("p", r["first_order"]))

    b.append(Block("h2", "4. Parts made to drawing"))
    b.append(Block("table", widths=[1.1, 1.4, 0.8, 1.6, 1.6, 1.5, 2.2, 3.2],
                   header=["Part no.", "Part", "Qty/lamp", "Material", "Process", "Finish", "Drawing / STEP", "Notes"],
                   rows=[[pt["part_no"], pt["name"], str(pt["quantity"]), pt["material"] or "TBD", pt["process"] or "TBD",
                          pt["finish"] or "—", f"{pt['drawing'].split('/')[-1]} (.pdf/.svg), {pt['step'].split('/')[-1]}",
                          "; ".join(["UNVERIFIED: " + u for u in pt["unverified"][:1]] + ["SAFETY: " + s for s in pt["safety"][:1]])]
                         for pt in c["parts"]]))
    b.append(Block("p", "Material and process are our current choice; please propose alternatives if they would be "
                        "better or cheaper without breaking the design constraint."))
    b.append(Block("p", "Tolerances: " + r.get("tolerances", "to be agreed.")))

    brass = [pt for pt in c["parts"] if (pt["material"] or "").lower().startswith("brass")]
    if brass:
        b.append(Block("h2", "5. Brass parts: please quote two ways"))
        b.append(Block("p", "For each brass part, please quote (A) your preferred method and (B) the near-net basis below "
                            "(turned from tube, ring blanks or close-fitting bar, or spun from a disc, rather than machined "
                            "from solid bar). Tell us the blank or stock size you would buy for each."))
        mass_g = (c["mass"] or {}).get("parts_kg", {})
        b.append(Block("table", widths=[0.9, 1.4, 1.5, 0.9, 2.0, 3.3],
                       header=["Part no.", "Part", "Finished size (mm)", "Finished mass (g)", "A: your preferred method",
                               "B: near-net basis"],
                       rows=[[pt["part_no"], pt["name"], pt["size_mm"] or "—",
                              f"{mass_g[pt['cad_key']] * 1000:.0f}" if pt["cad_key"] in mass_g else "—",
                              "Your choice (state it)", NEAR_NET_BASIS.get(pt["cad_key"], "Near-net blank of your choice")]
                             for pt in brass]))

    b.append(Block("h2", "6. Bought-in parts, hardware and operations"))
    ops = [it for it in c["bought_in"] if it["group"] == "operation"]
    if ops:
        b.append(Block("p", "Operations to include in the price of the part they are done on:"))
        b.append(Block("bullets", items=[f"{it['name']}" + (f" (on the {it['on_part'].replace('_', ' ')})" if it["on_part"] else "")
                                         for it in ops]))
    b.append(Block("p", "Hardware and bought-in parts (quote them if you supply them, or tell us to supply them):"))
    rows = [[h["item"], h["name"], f"{h['quantity']:g}", h["material"], h["notes"]] for h in c["hardware"]]
    rows += [["—", it["name"], f"{it['quantity']:g}", "", ""] for it in c["bought_in"] if it["group"] == "hardware"]
    b.append(Block("table", widths=[0.6, 3.6, 0.7, 1.6, 3.0], header=["Item", "Component", "Qty/lamp", "Material", "Notes"],
                   rows=rows))
    elec = [it for it in c["bought_in"] if it["group"] == "electronics"]
    b.append(Block("p", "Electronics are sourced through a separate RFQ to electronics suppliers and are not part of this "
                        "quote: " + "; ".join(it["name"].split(":")[0] for it in elec) + ". Their space is shown in the "
                        "assembly STEP. If you can offer final assembly, please quote fitting them, wiring, the light-up "
                        "/ charge / dimming test and packing."))

    b.append(Block("h2", "7. Price breakdown requested"))
    b.append(Block("p", "For each part and each quantity, please break the unit price down as below so we can compare it "
                        "line by line between suppliers, in the currency and on the Incoterms of the commercial terms section. Brass parts: one row for "
                        "method A and one for method B."))
    first = next((pt for pt in c["parts"] if pt not in brass), c["parts"][0] if c["parts"] else None)
    example = []
    if first:
        example += [[first["part_no"], "—", f"{q:,}", "", "", "", "", "", "", ""] for q in QUANTITY_TIERS]
    if brass:
        ex = next((pt for pt in brass if pt["cad_key"] == "gallery"), brass[0])
        example += [[ex["part_no"], m, f"{q:,}", "", "", "", "", "", "", ""] for m in ("A", "B") for q in QUANTITY_TIERS]
    b.append(Block("table", header=["Part no.", "Method", "Qty", "Material (£)", "Cycle time (min)", "Process (£)",
                                    "Finishing (£)", "Setup per batch (£)", "Tooling one-off (£)", "Unit price (£)"],
                   rows=example + [["…", "", "", "", "", "", "", "", "", ""]]))
    b.append(Block("p", "(£) means the amount in your currency. Please also state: material grade and the blank / stock "
                        "size you buy per part, the machine or process used, and who owns the tooling."))

    b.append(Block("h2", "8. Questions for the supplier"))
    b.append(Block("bullets", items=[
        "Minimum order quantity (MOQ) per part and for the assembled lamp.",
        "Tooling: what is needed, one-off cost, lead time, ownership and expected life.",
        "Lead time: tooling, first samples and production, for each quantity.",
        "Samples: cost and timing for first-off samples and for the golden sample.",
        "Suggested design changes that would cut cost or risk without changing the look (DFM feedback).",
        "Finishing: lacquer / plating process, colour matching method and the minimum charge per part and per batch.",
        "Packing and shipping: please quote your standard protective packing (cartons per pallet, how the glass is "
        "protected). The retail box is briefed separately.",
        "Final assembly: can you offer final assembly, the electronics fitting, the light-up / charge / dimming test and "
        "packing? If so, please quote it separately.",
        "Adhesive: please propose the structural adhesive for the tower, gallery, frame and spigot bonds (for example a "
        "two-part methacrylate or epoxy), to be proven by a pull-test on samples.",
        "Marking: " + r.get("marking", "to be agreed."),
    ]))

    b.append(Block("h2", "9. Premium quality requirements"))
    b.append(Block("bullets", items=[
        "Class A cosmetic surfaces on all visible parts: no spinning marks, dents, scratches, inclusions or orange peel, "
        "inspected at 50 cm under daylight.",
        "Gloss and colour match: against the physical colour samples we supply (and between parts of the same colour).",
        f"Minimum wall thickness {p['wall_thickness']:g} mm on spun parts after forming, for a solid feel (UNVERIFIED).",
        "Weight plate clamped by the three band screws so nothing rattles; shake test.",
        "Windows: clean laser-cut edges, deburred, masked so the lacquer line is crisp; even glow through every window.",
        f"Target total lamp mass {target_mass:g} kg ± 10%." if target_mass else "Target total lamp mass: to be agreed.",
        "Masked two-tone line level all round; lantern glass sits square with no rattle; cap twists on smoothly to a "
        "positive stop.",
        "Golden sample approval before production; production inspected against the approved golden sample. "
        + r.get("aql", "AQL to be agreed."),
    ]))

    b += _commercial(c)

    b.append(Block("h2", "Unverified values and safety items"))
    unv = [f"{pt['part_no']} {pt['name']}: {u}" for pt in c["parts"] for u in pt["unverified"]]
    b.append(Block("bullets", items=[f"UNVERIFIED: {u}" for u in unv] or ["None listed."]))
    seen = set()
    safety = []
    for f in c["flags"]:
        key = (f["part"], f["text"])
        if key not in seen:
            seen.add(key)
            safety.append(f"SAFETY: {f['part']}: {f['text']}")
    b.append(Block("bullets", items=safety or ["None listed."]))

    b.append(Block("h2", "11. Attachments"))
    b.append(Block("bullets", items=[
        "drawings/: one PDF and one SVG per made-to-drawing part (general tolerance ISO 2768-m unless stated).",
        "artwork/: FARO nameplate lettering, 1:1 vector (SVG and DXF; layer LETTERING_ETCH, plate outline for reference).",
        "artwork/: knob logo, 1:1 vector (SVG and DXF; layer LOGO_ENGRAVE is the engraved area, knob outline for reference).",
        "step/: one STEP file per made-to-drawing part, plus the full assembly.",
        "bom.csv: full bill of materials (part numbers, materials, processes; electronics marked as a separate RFQ).",
        "rfq.md / rfq.pdf: this document.",
    ]))
    return _numbered(b)


def electronics_rfq_blocks(c: dict[str, Any]) -> list[Block]:
    """Separate RFQ for battery / electronics suppliers: pack, control board and LEDs."""
    project: Project = c["project"]
    p = c["params"]
    d = faro.derived({k: float(v) for k, v in p.items()})
    rt = c.get("runtime") or {}
    spec = (load_template(project.template).get("electrical") or {}) if project.template else {}
    bat = spec.get("battery", {})
    loads = {ld["part"]: ld["watts"] for ld in spec.get("loads", [])}
    bl, bw, bt = faro.BATTERY
    r = _rfq_settings(project)
    b: list[Block] = _header(c, f"Request for quotation: {project.name} table lamp (battery pack, control board and LEDs)")
    b.append(Block("warn", "Values marked UNVERIFIED are our working assumptions: confirm them or propose better. Items "
                           "marked COMPLIANCE or SAFETY must be backed by certificates and test reports for the exact part."))

    b.append(Block("h2", "1. Product"))
    b.append(Block("p", "A cordless decorative table lamp in spun aluminium and brass, 300 mm tall: a frosted glass lantern "
                        "at the top and five glowing windows in the tower. The metalwork is quoted separately; this RFQ "
                        "covers the battery pack, the control board and the two LED light sources."))

    b.append(Block("h2", "2. Quantities and samples"))
    b.append(Block("bullets", items=[
        "Please quote each of these order quantities: " + ", ".join(f"{q:,}" for q in QUANTITY_TIERS) + " sets "
        "(one set = one battery pack, one control board, one lantern LED module, one tower light). Tell us your MOQ.",
        "Samples: please quote 5 sample sets and the lead time.",
        *([r["first_order"].replace("lamps", "sets")] if r.get("first_order") else []),
    ]))

    b.append(Block("h2", "3. Battery pack: pre-certified 2 x 18650"))
    cap = bat.get("cell_capacity_mah", 3350)
    b.append(Block("bullets", items=[
        f"Two branded 18650 Li-ion cells, about {cap:,} mAh class (name the cell brand and model).",
        "Configuration: 1S2P (3.6 V nominal), so USB-C charging stays simple. If you strongly prefer 2S (7.2 V), quote it "
        "as an alternative with your reasons.",
        "Protection circuit in the pack: over-charge, over-discharge, over-current and short circuit, plus an NTC "
        "thermistor so charging stops outside a safe temperature range.",
        "Pass-through charging: the lamp must work normally while it charges from USB-C. Charging with the lamp on must "
        "not cycle or over-stress the cells. Tell us whether the power path is on the pack or on the control board.",
        f"Size: it must fit within {bl:g} × {bw:g} × {bt:g} mm lying flat (cells side by side), with leads.",
        "Leads and a polarised connector to the control board (for example JST PH 2.0), about 80 mm long (UNVERIFIED). "
        "The end user must be able to replace the pack with ordinary tools.",
        "COMPLIANCE: the pack must be pre-certified. Send the UN38.3 test summary and the IEC 62133-2 test report for this "
        "exact pack (cells, configuration and protection board), plus the safety data sheet. Pack labelling must follow "
        "UK requirements (crossed-out wheelie bin, capacity in mAh/Wh); if CE for the EU follows, EU Batteries Regulation "
        "2023/1542 labelling too.",
    ]))

    b.append(Block("h2", "4. Control board"))
    lw, tw = loads.get("led_module", 1.5), loads.get("tower_light", 0.8)
    b.append(Block("bullets", items=[
        f"USB-C receptacle (5 V input; no USB PD needed; CC resistors so C-to-C cables work). It mounts on the board at the "
        f"rear of the base, receptacle centre {faro.USBC_Z:g} mm above the base underside. Board envelope about 40 × 25 mm "
        "(UNVERIFIED; tell us your size).",
        "Li-ion charger for the pack with the NTC input, and the pass-through power path (section 3).",
        f"Two constant-current LED channels: lantern about {lw:g} W and tower light about {tw:g} W (UNVERIFIED). Match the "
        "voltage and current to the LEDs you quote.",
        "Dimming from a slim rotary potentiometer with switch (9 mm class, D-shaft, M7 bushing), mounted in the tower. "
        "Switch off at the end of travel. Both channels dim together, with the tower at a fixed share of the lantern set "
        "at the factory. Smooth dimming down to 5% or lower, with no visible flicker (PWM at 3 kHz or more, or analogue "
        "dimming: IEEE 1789 low-risk).",
        "Please quote the potentiometer and its harness too.",
        "Low battery: the lantern blinks twice, then the lamp dims and switches off before the cells are deeply "
        "discharged. Standby current 50 µA or less (UNVERIFIED).",
        "A small charging indicator LED next to the USB-C port. No other indicator on the lamp.",
        "Wiring harness: about 250 mm from the base to the lantern LED through the tower, plus leads to the tower light "
        "and the potentiometer, with connectors.",
        "COMPLIANCE: please quote USB-C charging and the board tested and documented for UKCA marking (UK launch): EMC "
        "(BS EN IEC 55015 and BS EN 61547), safety (BS EN IEC 62368-1 or BS EN 60598-1 as applicable) and RoHS. CE for the "
        "EU may follow: tell us what it would add. Send the test reports; we will check them with an accredited test lab.",
    ]))

    b.append(Block("h2", "5. LEDs"))
    tl = d["diffuser_length"] - 2 * faro.DIFFUSER_OVERLAP
    b.append(Block("bullets", items=[
        f"Lantern LED module: a round aluminium-core board Ø{faro.LED_BOARD_D:g} mm on a heat spreader. Emitter area "
        f"Ø{faro.LED_EMITTER_D:g} mm or less, total height {faro.LED_H:g} mm or less, 2700 K, CRI 90 or more (R9 above "
        f"50 preferred), about {lw:g} W. It lights a frosted glass lantern from below; the board rests on a ledge.",
        f"Tower light: {faro.FILAMENTS} warm-white LED filament strips, 2700 K, about {tw:g} W in total, about "
        f"{tl:.0f} mm of light along a Ø{faro.SPINE_D:g} mm aluminium spine. The tube behind the windows is "
        f"{d['diffuser_length']:.0f} mm long. Please quote with and without the spine.",
        "Colour consistency: 3-step MacAdam binning. Please send datasheets, and LM-80 reports if you have them.",
        "COMPLIANCE: light sources must meet the UK ecodesign and energy labelling rules for light sources (the GB versions "
        "of EU 2019/2020 and 2019/2015) where they apply; please confirm.",
    ]))

    b.append(Block("h2", "6. Runtime"))
    b.append(Block("p", f"Target: at least {rt['target_h']:g} h at full brightness with both lights on. Our estimate is "
                        f"{rt['hours']:.1f} h from {rt['battery_wh']:.1f} Wh and {rt['load_w']:.1f} W (UNVERIFIED). "
                        "Please give your own runtime and charge time for what you quote."
                   if rt.get("applicable") and rt.get("hours") and rt.get("target_h") else "Runtime target: to be agreed."))

    b.append(Block("h2", "7. Alternatives to quote"))
    b.append(Block("bullets", items=[
        "Option B (mains, no battery): a certified external 12 V adapter (UK plug; EU plug may follow), a low-voltage cable and an "
        "internal DC-DC constant-current driver for both channels, with the same dimming.",
        "Capacitive touch dimming on the brass finial instead of the knob.",
    ]))

    b.append(Block("h2", "8. Price breakdown requested"))
    b.append(Block("table", header=["Item", "Qty", "Unit price", "Tooling / NRE (one-off)", "Certification (one-off)",
                                    "MOQ", "Lead time"],
                   rows=[[item, f"{q:,}", "", "", "", "", ""]
                         for item in ("Battery pack", "Control board + potentiometer + harness", "Lantern LED module",
                                      "Tower light") for q in QUANTITY_TIERS]))
    b += _commercial(c)

    b.append(Block("h2", "9. Questions for the supplier"))
    b.append(Block("bullets", items=[
        "Datasheets for the cells, the protection board, the charger and driver ICs, and the LEDs.",
        "Certificates and test reports: what exists already and what needs testing, with cost and time.",
        "Shipping: how you ship the pack (UN3480 alone, or UN3481 packed with equipment) and any surcharge.",
        "Warranty, country of origin, and the shelf life and storage charge level of the packs.",
        "Suggested changes that would cut cost or risk.",
    ]))

    b.append(Block("h2", "10. Space available (from our CAD)"))
    b.append(Block("table", header=["Item", "Space"], rows=[
        ["Battery bay in the base", f"{bl:g} × {bw:g} × {bt:g} mm, lying flat; inside height of the base "
                                    f"{d['base_inner_height']:.1f} mm"],
        ["Control board", f"about 40 × 25 mm at the base rear; USB-C centre {faro.USBC_Z:g} mm above the underside"],
        ["Lantern LED board", f"Ø{faro.LED_BOARD_D:g} mm, rests on the gallery ledge (Ø{faro.LEDGE_BORE:g} mm bore); it lifts "
                              f"out through a Ø{d['led_access_dia']:.0f} mm opening"],
        ["Tower light", f"Ø{faro.SPINE_D:g} mm spine, {d['gallery_top_z'] - faro.LEDGE_T - 0.5 - p['base_height']:.0f} mm "
                        f"long; Ø{d['diffuser_od'] - 2 * faro.DIFFUSER_WALL:.0f} mm clear inside the diffuser tube"],
        ["Potentiometer", f"Ø{faro.POT_D:g} × {faro.POT_DEPTH:g} mm body behind the tower wall, M7 bushing"],
    ]))

    b.append(Block("h2", "11. Battery compliance (for your information)"))
    b.append(Block("bullets", items=[f"COMPLIANCE: {x}" for x in rt.get("compliance", [])] or ["None listed."]))
    return _numbered(b)


def supplier_bom_csv(c: dict[str, Any]) -> str:
    """BOM for suppliers: part numbers, materials and processes, without any cost or internal flags."""
    import csv

    drawn = {pt["cad_key"]: pt for pt in c["parts"]}
    buf = io.StringIO()
    w = csv.writer(buf)
    colours = _colour_refs(c)
    w.writerow(["Part no.", "Part", "Qty/lamp", "Material", "Process", "Finish", "Colour reference", "Gloss", "Size (mm)",
                "Supply", "Drawing / STEP", "Notes"])
    for r in c["bom"]["rows"]:
        key = r.get("cad_key")
        item = str(r["item"])
        if key in drawn:
            pt = drawn[key]
            supply, files = "Made to drawing", f"{pt['drawing'].split('/')[-1]}.pdf; {pt['step'].split('/')[-1]}"
            if key == "nameplate":
                files += f"; artwork/{nameplate.STEM}.svg / .dxf"
            if key == "knob":
                files += f"; artwork/{logo.STEM}.svg / .dxf"
            notes = "; ".join(["UNVERIFIED: " + u for u in pt["unverified"]] + ["SAFETY: " + x for x in pt["safety"]])
        elif key in ELECTRONIC_PARTS:
            supply, files, notes = "Electronics (separate RFQ)", "", "COMPLIANCE: certified for UK sale (UKCA)"
        else:
            supply, files, notes = "Bought-in", "", r.get("supplier_notes") or ""
        part_no = f"F-{int(item):02d}" if item.isdigit() else item
        colour, gloss = colours.get(key or "", ("", ""))
        w.writerow([part_no, r["name"], f"{r['quantity']:g}", r["material"], r["process"], r["finish"],
                    colour, gloss, r["size_mm"], supply, files, notes])
    return buf.getvalue()


_MONEY = re.compile(r"£\s?\d")


def consistency_checks(project: Project, c: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Is the pack consistent with the latest CAD, the parts' processes and the production changes?"""
    from app.services.costdown import cad_mismatches

    c = c or pack_contents(project)
    rules = load_rules()
    out: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        out.append({"check": name, "ok": bool(ok), "detail": detail})

    model = latest_model(project)
    if model is None:
        check("CAD generated", False, "Generate CAD first: drawings and STEP files come from the latest CAD version.")
        return out
    # Drawings are cut from solids built now; STEP files were saved when the CAD was generated. If the generator
    # changed in between (e.g. a new production change), they disagree: compare volumes part by part.
    built = faro.model(c["params"]).parts
    info = model.part_info or {}
    differ = [pt["part_no"] + " " + pt["name"] for pt in c["parts"]
              if pt["cad_key"] in info and pt["cad_key"] in built
              and abs(built[pt["cad_key"]].volume - info[pt["cad_key"]]["volume_mm3"]) > 0.005 * info[pt["cad_key"]]["volume_mm3"] + 1]
    check("Drawings and STEP files show the same solids", not differ,
          f"CAD v{model.version}: drawings and STEP agree for all {len(c['parts'])} parts" if not differ else
          f"CAD v{model.version} was generated with an older generator ({', '.join(differ)}); regenerate CAD")
    bodies = set((model.part_info or {}).keys())
    check("All bodies in the model", set(faro.PART_KEYS) <= bodies,
          f"{len(bodies)} bodies" + ("" if set(faro.PART_KEYS) <= bodies else
                                    f"; missing {', '.join(sorted(set(faro.PART_KEYS) - bodies))}"))
    steps = {o.part_key: o.path for o in model.outputs if o.format == "step" and o.part_key}
    missing = [pt["part_no"] for pt in c["parts"] if pt["cad_key"] not in steps
               or not (settings.data_dir / steps[pt["cad_key"]]).is_file()]
    check("STEP file for every drawing", not missing,
          f"{len(c['parts'])} drawings, {len(c['parts']) - len(missing)} STEP files" + (f"; missing {missing}" if missing else ""))
    stale = []
    for pt in c["parts"]:
        need = dr.NOTE_PROCESS.get(pt["cad_key"])
        if need and rules.processes[need].name != pt["process"]:
            stale.append(f"{pt['part_no']} {pt['name']}: drawing notes assume {rules.processes[need].name.lower()}, "
                         f"part is {(pt['process'] or 'TBD').lower()}")
    check("Drawing notes match each part's process", not stale, "; ".join(stale) or "all match")
    mism = cad_mismatches(project)
    check("CAD shows every chosen route's design changes", not mism,
          "; ".join(f"{m['part']}: {', '.join(m['changes'])}" for m in mism) or "no mismatches")
    for g in faro.production_change_checks(c["params"]):
        check(f"Production change: {g['feature']}", g["ok"], g["detail"])
    rows = {r.get("cad_key") for r in c["bom"]["rows"]}
    check("BOM lists every drawn part", all(pt["cad_key"] in rows for pt in c["parts"]), "part numbers F-xx follow the BOM items")
    mass = c.get("mass") or {}
    check("Mass near target", mass.get("status") in ("ok", None),
          f"{mass.get('total_kg', 0):.2f} kg vs target {mass.get('target_kg')} kg ({mass.get('status')})")
    texts = {"rfq": rfq_markdown(rfq_blocks(c)), "electronics rfq": rfq_markdown(electronics_rfq_blocks(c)),
             "bom.csv": supplier_bom_csv(c)}
    leaks = [name for name, t in texts.items() if _MONEY.search(t)]
    check("No prices or cost targets in supplier documents", not leaks, "clean" if not leaks else f"£ amounts in {leaks}")
    allowed = {ph for _, _, ph in CONTACT_FIELDS}
    found = sorted({m for t in texts.values() for m in re.findall(r"\[[A-Z][A-Z ,]+[^\]]*\]", t)})
    stray = [m for m in found if m not in allowed]
    check("No stray placeholders in the RFQs", not stray,
          ("only the contact fields still blank: " + ", ".join(found) if found else "none") if not stray else
          f"unexpected: {', '.join(stray)}")
    missing = missing_contact(project)
    out.append({"check": "Contact and delivery details filled in", "ok": not missing, "level": "warn",
                "detail": "all filled in" if not missing else
                "empty: " + ", ".join(missing) + " (Factory Pack tab); the RFQs show placeholders for them"})
    built_info = faro.model(c["params"]).info
    for name, ok, detail in nameplate.consistency(model.part_info or {}, built_info):
        check(name, ok, detail)
    for name, ok, detail in logo.consistency(logo.logo_radius(float(c["params"]["knob_diameter"])), built_info):
        check(name, ok, detail)
    open_q = [q["question"] for q in open_questions(project, c) if q["status"] == "open"]
    check("Supplier questions answered", not open_q, "all answered" if not open_q else "; ".join(open_q))
    return out


def open_questions(project: Project, c: dict[str, Any]) -> list[dict[str, str]]:
    """Supplier questions: the template's list (resolved once it has an `answer`) plus project assumptions."""
    tpl = load_template(project.template) if project.template else {}
    out = []
    for q in tpl.get("rfq_open_questions", []):
        item = {k: q[k] for k in ("id", "topic", "question", "why", "proposed")}
        item["answer"] = q.get("answer", "")
        item["status"] = "resolved" if q.get("answer") else "open"
        out.append(item)
    labels = {
        "production_volume": ("Commercial", "Production volume is still TBD.",
                              "The RFQ asks for 300 / 500 / 2,000; suppliers will ask which you expect to order first.",
                              "Say which quantity is the likely first order."),
        "intended_markets": ("Compliance", "Intended markets are an assumption.",
                             "Sets the marking, plug types and the battery rules.", "Confirm the launch markets."),
        "approx_dimensions": ("Drawings", "Overall dimensions are a placeholder.", "Every drawing scales from them.",
                              "Confirm the dimensions on the Overview tab."),
    }
    have = {q["id"] for q in out}
    for f in c.get("assumed", []):
        if f in labels and f not in have:
            topic, question, why, proposed = labels[f]
            out.append({"id": f, "topic": topic, "question": question, "why": why, "proposed": proposed, "answer": "",
                        "status": "open"})
    return out


def placeholders(project: Project) -> list[str]:
    """Bracketed fields still left in the RFQs: the contact fields you haven't filled in."""
    values = contact(project)
    return [ph for k, _, ph in CONTACT_FIELDS if not values[k]]


def rfq_markdown(blocks: list[Block]) -> str:
    out: list[str] = []
    for blk in blocks:
        if blk.kind == "h1":
            out += [f"# {blk.text}", ""]
        elif blk.kind == "h2":
            out += [f"## {blk.text}", ""]
        elif blk.kind == "p":
            out += [blk.text, ""]
        elif blk.kind == "warn":
            out += [f"> **{blk.text}**", ""]
        elif blk.kind == "bullets":
            out += [f"- {i}" for i in blk.items or []] + [""]
        elif blk.kind == "table":
            out.append("| " + " | ".join(blk.header or []) + " |")
            out.append("|" + "---|" * len(blk.header or []))
            for r in blk.rows or []:
                out.append("| " + " | ".join(x.replace("|", "/") for x in r) + " |")
            out.append("")
    return "\n".join(out)


def rfq_pdf(blocks: list[Block], title: str = "Request for quotation") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("s", parent=body, fontSize=7.5, leading=9.5)
    warn = ParagraphStyle("w", parent=body, textColor=colors.HexColor("#8a1c14"), backColor=colors.HexColor("#fbeae8"),
                          borderPadding=5, spaceBefore=4, spaceAfter=8)

    def esc(s: str) -> str:
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for tag, col in (("UNVERIFIED:", "#8a5a00"), ("SAFETY:", "#b3261e"), ("COMPLIANCE:", "#1f4e9c")):
            s = s.replace(tag, f'<font color="{col}"><b>{tag}</b></font>')
        return s

    flow = []
    for blk in blocks:
        if blk.kind == "h1":
            flow += [Paragraph(esc(blk.text), ss["Title"])]
        elif blk.kind == "h2":
            flow += [Spacer(1, 4), Paragraph(esc(blk.text), ss["Heading2"])]
        elif blk.kind == "p":
            flow.append(Paragraph(esc(blk.text), body))
        elif blk.kind == "warn":
            flow.append(Paragraph(f"<b>{esc(blk.text)}</b>", warn))
        elif blk.kind == "bullets":
            flow.append(ListFlowable([ListItem(Paragraph(esc(i), body), leftIndent=10) for i in blk.items or []],
                                     bulletType="bullet", start="•", leftIndent=10))
        elif blk.kind == "table":
            data = [[Paragraph(f"<b>{esc(h)}</b>", small) for h in blk.header or []]]
            data += [[Paragraph(esc(x), small) for x in r] for r in blk.rows or []]
            avail = A4[0] - 30 * mm
            col_w = [avail * w / sum(blk.widths) for w in blk.widths] if blk.widths else None
            t = Table(data, repeatRows=1, hAlign="LEFT", colWidths=col_w)
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#999999")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef0f3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            flow += [t, Spacer(1, 6)]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                            title=title, author="Bathsheva London")
    doc.build(flow)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Drawings and the zip
# ---------------------------------------------------------------------------


def part_sheet(c: dict[str, Any], cad_key: str) -> dr.PartSheet:
    pt = next((x for x in c["parts"] if x["cad_key"] == cad_key), None)
    if pt is None:
        raise FactoryPackError(f"No made-to-drawing part {cad_key!r}")
    return dr.PartSheet(cad_key, pt["part_no"], pt["name"], pt["material"], pt["process"], pt["finish"], pt["quantity"],
                        c["project"].name, c["cad_version"], c["date"], pt["unverified"], pt["safety"])


def drawing_files(c: dict[str, Any], cad_key: str) -> tuple[str, bytes]:
    d = dr.part_drawing(c["params"], part_sheet(c, cad_key))
    return dr.to_svg(d), dr.to_pdf(d)


def readme(c: dict[str, Any], folder: str) -> str:
    return "\n".join([
        f"{c['project'].name} table lamp: request for quotation pack ({c['date']}, CAD v{c['cad_version']})",
        "",
        "mechanical/   for metalwork, glass and finishing suppliers:",
        "              rfq.pdf (and rfq.md), drawings/ (PDF + SVG per part), step/ (STEP per part + assembly), bom.csv,",
        "              artwork/ (FARO nameplate lettering and knob logo, 1:1 SVG and DXF)",
        "electronics/  for battery and electronics suppliers:",
        "              rfq_electronics.pdf (and .md): pre-certified 2 x 18650 pack, control board with dimming, LEDs",
        "",
        "Quantities to quote: " + ", ".join(f"{q:,}" for q in QUANTITY_TIERS) + " units.",
        "Units: millimetres. Values marked UNVERIFIED are working assumptions; SAFETY and COMPLIANCE items need certificates.",
        "",
    ])


def build_factory_pack(project: Project) -> tuple[str, bytes]:
    model = latest_model(project)
    if model is None:
        raise FactoryPackError("Generate CAD first: the pack includes the latest CAD version's STEP files.")
    c = pack_contents(project)
    steps = {o.part_key: o.path for o in model.outputs if o.format == "step" and o.part_key}
    assembly = next((o.path for o in model.outputs if o.format == "step" and o.part_key is None), None)
    blocks = rfq_blocks(c)
    eblocks = electronics_rfq_blocks(c)
    folder = f"{project.slug}_rfq_pack_v{model.version}"
    mech, elec = f"{folder}/mechanical", f"{folder}/electronics"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{folder}/README.txt", readme(c, folder))
        zf.writestr(f"{mech}/rfq.md", rfq_markdown(blocks))
        zf.writestr(f"{mech}/rfq.pdf", rfq_pdf(blocks, "Request for quotation: metalwork, glass and finishing"))
        zf.writestr(f"{mech}/bom.csv", supplier_bom_csv(c))
        for pt in c["parts"]:
            svg, pdf = drawing_files(c, pt["cad_key"])
            zf.writestr(f"{mech}/{pt['drawing']}.svg", svg)
            zf.writestr(f"{mech}/{pt['drawing']}.pdf", pdf)
            if pt["cad_key"] in steps:
                zf.write(settings.data_dir / steps[pt["cad_key"]], f"{mech}/{pt['step']}")
        if assembly:
            zf.write(settings.data_dir / assembly, f"{mech}/step/{project.slug}_assembly.step")
        for fname, data in nameplate.artwork_files().items():
            zf.writestr(f"{mech}/artwork/{fname}", data)
        for fname, data in logo.artwork_files(logo.logo_radius(float(c["params"]["knob_diameter"]))).items():
            zf.writestr(f"{mech}/artwork/{fname}", data)
        zf.writestr(f"{elec}/rfq_electronics.md", rfq_markdown(eblocks))
        zf.writestr(f"{elec}/rfq_electronics.pdf", rfq_pdf(eblocks, "Request for quotation: battery, control board and LEDs"))
    return f"{folder}.zip", buf.getvalue()


def pack_summary(project: Project) -> dict[str, Any]:
    """JSON for the Factory Pack tab: what goes in the pack and what still needs checking."""
    c = pack_contents(project)
    blocks = rfq_blocks(c)
    unverified = [f"{pt['part_no']} {pt['name']}: {u}" for pt in c["parts"] for u in pt["unverified"]]
    return {
        "cad_version": c["cad_version"], "ready": c["cad_version"] is not None,
        "parts": [{k: v for k, v in pt.items()} for pt in c["parts"]],
        "bought_in": c["bought_in"], "hardware": c["hardware"], "quantity_tiers": QUANTITY_TIERS, "mass": c["mass"],
        "brass_parts": [{"part_no": pt["part_no"], "name": pt["name"], "near_net": NEAR_NET_BASIS.get(pt["cad_key"], "")}
                        for pt in c["parts"] if (pt["material"] or "").lower().startswith("brass")],
        "unverified": unverified,
        "safety": sorted({f"{f['part']}: {f['text']}" for f in c["flags"]}),
        "compliance": ["All electronics (LEDs, control board, battery, dimmer; adapter and driver for option B) certified "
                       "for UK sale (UKCA; CE may follow); certificates to be verified by an accredited test lab.",
                       *[f"Battery: {x}" for x in (c.get("runtime") or {}).get("compliance", [])]],
        "runtime": c.get("runtime"),
        "production_changes": faro.PRODUCTION_CHANGES,
        "consistency": consistency_checks(project, c) if c["cad_version"] is not None else [],
        "open_questions": open_questions(project, c),
        "placeholders": placeholders(project),
        "contact": contact(project),
        "contact_fields": [{"key": k, "label": label, "placeholder": ph} for k, label, ph in CONTACT_FIELDS],
        "missing_contact": missing_contact(project),
        "rfq_markdown": rfq_markdown(blocks),
        "electronics_rfq_markdown": rfq_markdown(electronics_rfq_blocks(c)),
        "notes": ["Our cost estimates and targets are not included in anything sent to suppliers.",
                  "The zip has two folders: mechanical/ for metalwork, glass and finishing suppliers, electronics/ for "
                  "battery and electronics suppliers.",
                  "Drawings are generated from the current CAD parameters; generate CAD so the STEP files match."],
    }

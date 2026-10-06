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
from app.models import Project
from app.rules.data import load_rules
from app.services.bom import bom_csv, build_bom
from app.services.cad import current_parameters, latest_model, mass_estimate
from app.services.recommendations import project_recommendations
from app.services.templates import load_template

QUANTITY_TIERS = [100, 500, 2000]

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
    if project.template != "faro":
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

    bought = []
    for it in _bought_in_lines(project, cost):
        bought.append(it)

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
        "project": project, "params": params, "bom": bom, "parts": parts, "bought_in": bought,
        "cad_version": latest.version if latest else None, "flags": flags, "mass": mass,
        "assumed": sorted(assumed), "date": date.today().isoformat(), "runtime": runtime,
    }


def _bought_in_lines(project: Project, cost) -> list[dict[str, Any]]:
    """Bought-in components (project cost items plus the route extras), without our prices."""
    from sqlalchemy.orm import object_session

    from app.services.costing import build_inputs

    session = object_session(project)
    out = []
    if session is None:
        return out
    inputs, ctx = build_inputs(session, project)
    drawn_extras = {"steel_weight_plate"}  # made to drawing: listed with the drawn parts instead
    for it in inputs.items:
        if it.unit != "pcs" or it.kind == "packaging":
            continue
        extra = ctx["extras"].get(it.item_id)
        if extra is not None and extra.price_key in drawn_extras:
            continue
        electronics = any(w in it.name.lower() for w in ("led", "driver", "adapter", "dimmer", "cable", "battery",
                                                         "board", "potentiometer", "usb"))
        out.append({"name": it.name, "quantity": it.quantity, "electronics": electronics})
    return out


# ---------------------------------------------------------------------------
# RFQ document
# ---------------------------------------------------------------------------


def rfq_blocks(c: dict[str, Any]) -> list[Block]:
    project: Project = c["project"]
    p = c["params"]
    mass = c["mass"] or {}
    target_mass = p.get("target_mass_kg")
    b: list[Block] = []
    b.append(Block("h1", f"Request for quotation: {project.name} table lamp"))
    b.append(Block("p", f"Bathsheva London · {c['date']} · CAD version "
                        f"{'v' + str(c['cad_version']) if c['cad_version'] else '(not generated)'} · units: millimetres"))
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
        "Base: spun aluminium shell, gloss black, with a laser-cut steel weight plate round the battery; aluminium bottom "
        "plate on four M2.5 screws so the user can replace the battery; felt pad on magnets.",
        "Cream band: turned aluminium ring; the base screws into it (three M3) and the tower is bonded on its spigot.",
        f"Tower: spun aluminium cone, two-tone lacquer (red lower section, masked line), {int(p['window_count'])} arched windows "
        "laser-cut after spinning, an opal borosilicate diffuser tube (window zone only) and a tower light behind them.",
        "Gallery and railing: spun brass shell with a soldered turned locating ring; photo-etched brass railing rolled into a ring (please also quote "
        "soldered brass wire and lost-wax casting).",
        "Lantern: frosted borosilicate tube inside a brass frame (rings turned from tube, soldered mullions); the red spun cap "
        "twist-locks onto the frame with a turned brass bayonet spigot (four lugs, 20° turn) and a brass ball finial.",
        "Construction: bonded and screwed, no central rod; no visible fixings.",
        "Cordless: 2 x 18650 Li-ion cells, USB-C charging, rotary dimmer with a solid brass knob on the tower.",
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

    b.append(Block("h2", "3. Quantities"))
    b.append(Block("p", "Please quote each of these order quantities: " + ", ".join(f"{q:,}" for q in QUANTITY_TIERS)
                        + " lamps. Tell us your MOQ if it is above any of them."))

    b.append(Block("h2", "4. Parts made to drawing"))
    b.append(Block("table", widths=[1.1, 1.4, 0.8, 1.6, 1.6, 1.5, 2.2, 3.2],
                   header=["Part no.", "Part", "Qty/lamp", "Material", "Process", "Finish", "Drawing / STEP", "Notes"],
                   rows=[[pt["part_no"], pt["name"], str(pt["quantity"]), pt["material"] or "TBD", pt["process"] or "TBD",
                          pt["finish"] or "—", f"{pt['drawing'].split('/')[-1]} (.pdf/.svg), {pt['step'].split('/')[-1]}",
                          "; ".join(["UNVERIFIED: " + u for u in pt["unverified"][:1]] + ["SAFETY: " + s for s in pt["safety"][:1]])]
                         for pt in c["parts"]]))
    b.append(Block("p", "Material and process are our current choice; please propose alternatives if they would be "
                        "better or cheaper without breaking the design constraint."))

    b.append(Block("h2", "5. Bought-in components"))
    b.append(Block("table", widths=[5, 1, 3], header=["Component", "Qty/lamp", "Notes"],
                   rows=[[it["name"], f"{it['quantity']:g}",
                          "COMPLIANCE: certified for UK/EU sale" if it["electronics"] else ""] for it in c["bought_in"]]))

    b.append(Block("h2", "6. Electronics: please quote the cordless baseline and option B"))
    runtime_line = (f"Runtime target: at least {rt['target_h']:g} h at full brightness with both lights on (our estimate "
                    f"{rt['hours']:.1f} h from {rt['battery_wh']:.1f} Wh and {rt['load_w']:.1f} W; UNVERIFIED)."
                    if rt.get("applicable") and rt.get("hours") and rt.get("target_h") else "Runtime target: to be agreed.")
    b.append(Block("bullets", items=[
        "Lantern LED: 2700 K, CRI ≥ 90, about 1.5 W, on a Ø38 mm board resting on the gallery ledge.",
        "Tower light: warm white LED filament strips (about 0.8 W) on a central spine behind the windows.",
        "Battery: pre-certified 2 x 18650 Li-ion pack (about 3,350 mAh branded cells, protection circuit), user-replaceable; "
        "the pack supplier provides the UN38.3 test summary and IEC 62133-2 report.",
        "Control board: USB-C charging, 2-cell charger, 2-channel constant-current LED driver, input for the rotary "
        "dimmer (slim 9 mm pot with switch, D-shaft).",
        runtime_line,
        "Option B (please also quote): certified external 12 V adapter (UK and EU plugs), low-voltage cable and an internal "
        "DC-DC constant-current driver for both channels; no battery.",
        "Alternative to quote: capacitive touch dimming on the brass finial instead of the knob.",
        "COMPLIANCE: electronics certified for UK and EU sale (UKCA / CE: electrical safety, EMC, RoHS, ecodesign for light "
        "sources). Send certificates and test reports; we will verify them with an accredited test lab.",
        *[f"COMPLIANCE (battery): {x}" for x in rt.get("compliance", [])],
    ]))

    b.append(Block("h2", "7. Price breakdown requested"))
    b.append(Block("p", "For each part and each quantity, please break the unit price down as below so we can compare it "
                        "line by line with our cost model."))
    b.append(Block("table", header=["Part no.", "Qty", "Material (£)", "Cycle time (min)", "Process (£)", "Finishing (£)",
                                    "Setup per batch (£)", "Tooling one-off (£)", "Unit price (£)"],
                   rows=[[pt["part_no"], f"{q:,}", "", "", "", "", "", "", ""] for pt in c["parts"][:2] for q in QUANTITY_TIERS]
                   + [["…", "", "", "", "", "", "", "", ""]]))
    b.append(Block("p", "Please also state: material grade and the blank / stock size you buy per part, the machine or "
                        "process used, and who owns the tooling."))

    b.append(Block("h2", "8. Questions for the supplier"))
    b.append(Block("bullets", items=[
        "Minimum order quantity (MOQ) per part and for the assembled lamp.",
        "Tooling: what is needed, one-off cost, lead time, ownership and expected life.",
        "Lead time: tooling, first samples and production, for each quantity.",
        "Samples: cost and timing for first-off samples and for the golden sample.",
        "Suggested design changes that would cut cost or risk without changing the look (DFM feedback).",
        "Finishing: lacquer / plating process, colour matching method and the minimum charge per part and per batch.",
        "Packing and shipping: cartons per pallet and how the glass is protected.",
    ]))

    b.append(Block("h2", "9. Premium quality requirements"))
    b.append(Block("bullets", items=[
        "Class A cosmetic surfaces on all visible parts: no spinning marks, dents, scratches, inclusions or orange peel, "
        "inspected at 50 cm under daylight.",
        "Gloss and colour match: to be agreed against an approved sample (and between parts of the same colour).",
        f"Minimum wall thickness {p['wall_thickness']:g} mm on spun parts after forming, for a solid feel (UNVERIFIED).",
        "Weight plate clamped by the three band screws so nothing rattles; shake test.",
        "Windows: clean laser-cut edges, deburred, masked so the lacquer line is crisp; even glow through every window.",
        f"Target total lamp mass {target_mass:g} kg ± 10%." if target_mass else "Target total lamp mass: to be agreed.",
        "Masked two-tone line level all round; lantern glass sits square with no rattle; cap twists on smoothly to a "
        "positive stop.",
        "Golden sample approval before production; production inspected against the approved golden sample "
        "(AQL to be agreed).",
    ]))

    b.append(Block("h2", "10. Unverified values and safety items"))
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
        "drawings/: one PDF and one SVG per made-to-drawing part (dimensions for quotation, tolerances to be agreed).",
        "step/: one STEP file per made-to-drawing part, plus the full assembly.",
        "bom.csv: full bill of materials.",
        "rfq.md / rfq.pdf: this document.",
    ]))
    return b


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


def rfq_pdf(blocks: list[Block]) -> bytes:
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
                            title="Request for quotation", author="Bathsheva London")
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


def build_factory_pack(project: Project) -> tuple[str, bytes]:
    model = latest_model(project)
    if model is None:
        raise FactoryPackError("Generate CAD first: the pack includes the latest CAD version's STEP files.")
    c = pack_contents(project)
    steps = {o.part_key: o.path for o in model.outputs if o.format == "step" and o.part_key}
    assembly = next((o.path for o in model.outputs if o.format == "step" and o.part_key is None), None)
    blocks = rfq_blocks(c)
    folder = f"{project.slug}_rfq_pack_v{model.version}"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{folder}/rfq.md", rfq_markdown(blocks))
        zf.writestr(f"{folder}/rfq.pdf", rfq_pdf(blocks))
        zf.writestr(f"{folder}/bom.csv", bom_csv(project))
        for pt in c["parts"]:
            svg, pdf = drawing_files(c, pt["cad_key"])
            zf.writestr(f"{folder}/{pt['drawing']}.svg", svg)
            zf.writestr(f"{folder}/{pt['drawing']}.pdf", pdf)
            if pt["cad_key"] in steps:
                zf.write(settings.data_dir / steps[pt["cad_key"]], f"{folder}/{pt['step']}")
        if assembly:
            zf.write(settings.data_dir / assembly, f"{folder}/step/{project.slug}_assembly.step")
    return f"{folder}.zip", buf.getvalue()


def pack_summary(project: Project) -> dict[str, Any]:
    """JSON for the Factory Pack tab: what goes in the pack and what still needs checking."""
    c = pack_contents(project)
    blocks = rfq_blocks(c)
    unverified = [f"{pt['part_no']} {pt['name']}: {u}" for pt in c["parts"] for u in pt["unverified"]]
    return {
        "cad_version": c["cad_version"], "ready": c["cad_version"] is not None,
        "parts": [{k: v for k, v in pt.items()} for pt in c["parts"]],
        "bought_in": c["bought_in"], "quantity_tiers": QUANTITY_TIERS, "mass": c["mass"],
        "unverified": unverified,
        "safety": sorted({f"{f['part']}: {f['text']}" for f in c["flags"]}),
        "compliance": ["All electronics (LEDs, control board, battery, dimmer; adapter and driver for option B) certified "
                       "for UK/EU sale; certificates to be verified by an accredited test lab.",
                       *[f"Battery: {x}" for x in (c.get("runtime") or {}).get("compliance", [])]],
        "runtime": c.get("runtime"),
        "production_changes": faro.PRODUCTION_CHANGES,
        "rfq_markdown": rfq_markdown(blocks),
        "notes": ["Our cost estimates and targets are not included in anything sent to suppliers.",
                  "Drawings are generated from the current CAD parameters; generate CAD so the STEP files match."],
    }

"""Atelier's Factory Pack: RFQs (mechanical and electronics), drawings, STEP files, supplier BOM and artwork.

Same interface as Faro's pack (`app.services.factory_pack`), which also provides the shared machinery reused
here: contact details, the RFQ writers (markdown and PDF), supplier questions and the commercial terms.
Nothing sent to suppliers contains our cost estimates or targets.
"""

from __future__ import annotations

import io
import re
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

from app.cad import atelier
from app.config import settings
from app.costing.data import load_cost_data
from app.factory import atelier_drawings as adr
from app.factory import drawings as dr
from app.factory import logo
from app.models import Project
from app.rules.data import load_rules
from app.services import factory_pack as fp
from app.services.bom import build_bom
from app.services.cad import current_parameters, latest_model, mass_estimate
from app.services.factory_pack import Block, FactoryPackError
from app.services.recommendations import project_recommendations

MECHANICAL_TITLE = "Request for quotation: housing, metalwork and finishing"
ELECTRONICS_TITLE = "Request for quotation: Bluetooth audio electronics, driver and battery"
ELECTRONIC_PARTS = {"driver", "passive_radiator", "battery", "main_board"}
ELECTRONIC_ITEM_KEYS = {"speaker_driver_57", "passive_radiator_60x40", "speaker_main_board", "battery_pack_1s2p",
                        "battery_pack_1s2p_custom", "usb_c_receptacle_ip67", "rotary_encoder_push",
                        "status_led_light_pipe", "usb_c_cable_braided"}
DRAWN_ITEM_KEYS = {"speaker_chassis_set", "ballast_cup_steel", "fin_pad_tpu"}
HARDWARE_ITEM_KEYS = {"screw_m4_12", "screw_m25_cs", "stud_m4", "screw_m3", "o_ring_spigot", "structural_adhesive",
                      "butyl_damping", "acoustic_fabric_set"}
OPERATION_ITEM_KEYS = {"knob_logo_engrave": "knob", "knob_knurl": "knob", "collar_lettering_etch": "collar"}
OPERATION_TEXT = {
    "knob_logo_engrave": "Engrave the Bathsheva emblem 0.2 mm deep in the knob face, tone-on-tone (before PVD)",
    "knob_knurl": "Fine straight knurl on the knob edge (DIN 82 RAA 0.5), on the lathe (before PVD)",
    "collar_lettering_etch": "Laser-etch \"ATELIER\" 0.15 mm deep round the foot on the collar's underside (before PVD)",
}
LETTERING_STEM = "A-01_collar_lettering"


def pack_contents(project: Project) -> dict[str, Any]:
    params = current_parameters(project)
    if not atelier.validate(params).ok:
        raise FactoryPackError("The CAD parameters are invalid: fix them on the CAD tab first.")
    bom = build_bom(project)
    recs = {r["part_id"]: r for r in project_recommendations(project)}
    rules = load_rules()
    cost = load_cost_data()
    latest = latest_model(project)
    by_key = {r["cad_key"]: r for r in bom["rows"] if r.get("cad_key")}
    assumed = set(project.assumed_fields or [])
    parts = []
    for key in adr.DRAWN_PARTS:
        row = by_key.get(key)
        if row is None:
            continue
        unverified = []
        if row["status"] != "decided":
            unverified.append("material and process are the workbench's recommendation, not a decision")
        proc = next((pr for pr in rules.processes.values() if pr.name == row["process"]), None)
        if proc and proc.wall_mm and not proc.verified:
            unverified.append(f"wall thickness limits for {proc.name.lower()} come from unverified rule data")
        if key in ("ballast", "collar"):
            unverified.append("mass from estimated part weights; the ballast is at its largest size (no margin)")
        safety = []
        if key in ("fin", "ballast"):
            safety.append("Stability: static tip-over 18° or more on the three fin pads (IEC 62368-1); verify on a sample.")
        no = f"A-{int(row['item']):02d}"
        stem = f"{no}_{fp._slug(row['name'])}"
        parts.append({
            "cad_key": key, "part_no": no, "name": row["name"], "quantity": row["quantity"], "material": row["material"],
            "process": row["process"], "finish": row["finish"], "size_mm": row["size_mm"], "status": row["status"],
            "unverified": unverified, "safety": safety, "drawing": f"drawings/{stem}", "step": f"step/{stem}.step",
        })
    parts.sort(key=lambda pt: pt["part_no"])
    bought = fp._bought_in_lines(project, cost, drawn_item_keys=DRAWN_ITEM_KEYS, hardware_item_keys=HARDWARE_ITEM_KEYS,
                                 operation_item_keys=OPERATION_ITEM_KEYS, operation_text=OPERATION_TEXT,
                                 electronics_item_keys=ELECTRONIC_ITEM_KEYS)
    hardware = [{"item": r["item"], "name": r["name"], "quantity": r["quantity"], "material": r["material"],
                 "notes": r["supplier_notes"]} for r in bom["rows"] if str(r["item"]).startswith(("H", "R"))]
    from app.services.audio import project_audio
    from app.services.electrical import project_runtime

    return {
        "project": project, "params": params, "bom": bom, "parts": parts, "bought_in": bought, "hardware": hardware,
        "cad_version": latest.version if latest else None, "flags": [], "mass": mass_estimate(project),
        "assumed": sorted(assumed), "date": date.today().isoformat(), "runtime": project_runtime(project),
        "audio": project_audio(project), "stability": atelier.stability(params),
    }


# ---------------------------------------------------------------------------
# RFQs
# ---------------------------------------------------------------------------


def _colours_table(c: dict[str, Any]) -> Block:
    rows = []
    for col in fp._rfq_settings(c["project"]).get("colours", []):
        rows.append([col["name"], ", ".join(fp._part_names(c, col["parts"])), col["hex"], fp._ral_text(col), col["gloss"]])
    return Block("table", widths=[2.2, 3.4, 1.0, 2.4, 2.6], header=["Finish", "Parts", "Hex (design reference)",
                                                                    "RAL (approximate)", "Gloss / tolerance"], rows=rows)


def rfq_blocks(c: dict[str, Any]) -> list[Block]:
    project: Project = c["project"]
    p = c["params"]
    r = fp._rfq_settings(project)
    st = c["stability"]
    b: list[Block] = fp._header(c, f"Request for quotation: {project.name} rocket Bluetooth speaker (housing, metalwork and finishing)")
    b.append(Block("warn", "Values marked UNVERIFIED are design estimates or unverified data. Items marked SAFETY or "
                           "COMPLIANCE must be verified with a qualified engineer or accredited test lab before production."))
    b.append(Block("h2", "Product summary"))
    b.append(Block("p", " ".join(project.description.split())))
    b.append(Block("bullets", items=[
        f"Height {p['overall_height']:g} ±1 mm to the nose tip, body Ø{p['body_max_diameter']:g} ±0.5 at its widest, fin span "
        f"about {st['footprint_mm'][0]:.0f} mm, mass {p['target_mass_kg']:g} ±0.1 kg. Form and proportions follow our "
        "approved prototype; the STEP files are the reference.",
        f"Body: PC/ABS, injection moulded, {p['wall_thickness']:g} mm wall; primer, colour, two clear coats, polished.",
        "Gold parts, all gold PVD in one matched tone: 6061 nose cone (CNC turned, hollowed) and bezels (CNC, diamond-cut "
        "chamfer); Zamak 5 fins (die-cast, hollow, 3 mm wall), collar and foot (die-cast, foot machined); solid brass C360 "
        "knob (CNC turned, knurled, emblem engraved); stainless 304 grilles (0.5 mm, photo-etched hexagons, formed).",
        "Construction: an internal steel chassis carries the driver, radiator, boards and battery tray plate. Fins screw into "
        "it with M4 through slots in the shell. The nose cone sits on a spigot with an O-ring and a bayonet with a hidden "
        "detent. The base collar screws into the tray plate from below, with the screws hidden under the foot. No visible "
        "fasteners.",
    ]))
    b.append(Block("h2", "What we would like you to quote"))
    b.append(Block("p", r.get("first_order", "") + " Quantities: " + " / ".join(f"{q:,}" for q in fp.QUANTITY_TIERS) + "."))
    b.append(Block("table", widths=[1.0, 2.2, 0.6, 2.2, 2.6, 2.8], header=["Part no.", "Part", "Qty", "Material", "Process",
                                                                           "Finish"],
                   rows=[[pt["part_no"], pt["name"], f"{pt['quantity']:g}", pt["material"] or "TBD", pt["process"] or "TBD",
                          pt["finish"] or ""] for pt in c["parts"]]))
    ops = [x for x in c["bought_in"] if x["group"] == "operation"]
    if ops:
        b.append(Block("p", "Operations included in the parts above:"))
        b.append(Block("bullets", items=[f"{x['name']} ({x['on_part']})" for x in ops]))
    b.append(Block("h2", "Colours and finishes"))
    b.append(_colours_table(c))
    b.append(Block("p", r.get("colour_note", "")))
    b.append(Block("bullets", items=[
        "Gold PVD: fine brushed satin, one tone across brass, Zamak, aluminium and stainless parts (ΔE ≤ 1.5); base layers as "
        "your coater specifies (copper-nickel on zinc, nickel on brass). Grain horizontal as fitted.",
        "Red body: ≥ 90 GU, ΔE ≤ 1.0 to the master; Class A surface (no sink, weld lines or gate marks on view).",
        "Tests: cross-cut adhesion ISO 2409 class 0; 50-cycle rub; 48 h neutral salt spray on PVD; artificial sweat; UV "
        "ΔE ≤ 2 after 100 h.",
    ]))
    b.append(Block("h2", "Fit, feel and quality"))
    b.append(Block("bullets", items=[
        r.get("tolerances", ""), r.get("aql", ""),
        "Knob: 24 soft detents, torque 8–12 mNm, press 3–4 N with 0.4 mm travel, wobble ≤ 0.1 mm; 50,000 presses and "
        "20,000 rotations.",
        "Knuckle tap on the body sounds dull with no ring; no rattle in a 20 Hz–20 kHz sweep at full volume; no flex when "
        "lifted by the shell.",
        "Drop 0.5 m unpackaged; ISTA 2A packaged. Indoor use, 0–40 °C.",
    ]))
    b.append(Block("h2", "Battery replacement (service)"))
    b.append(Block("p", "The battery must be replaceable after removing the base collar, with standard tools only:"))
    b.append(Block("bullets", items=list(atelier.BATTERY_SERVICE)))
    b.append(Block("h2", "Where production departs from the prototype"))
    b.append(Block("table", widths=[2.0, 3.5, 5.5], header=["Feature", "Prototype", "Production"],
                   rows=[[x["feature"], x["prototype"], x["production"]] for x in atelier.PRODUCTION_CHANGES]))
    b.append(Block("h2", "Open points for your proposal"))
    b.append(Block("bullets", items=[f"UNVERIFIED: {x}" for x in atelier.OPEN_ITEMS]))
    b += fp._commercial(c)
    b.append(Block("h2", "What to include in your quote"))
    b.append(Block("bullets", items=[
        "Unit price per part at each quantity, with Material, Cycle time (min), Finishing and Tooling one-off shown separately.",
        "MOQ, tooling lead time, sample lead time and production lead time.",
        "Samples: first-off samples and a golden sample for approval.",
        "Final assembly: can you offer final assembly, sealing, the acoustic and pairing test and protective packing?",
        "Suggested design changes that would cut cost or risk (especially the body mould and the zinc dies).",
    ]))
    b.append(Block("h2", "Compliance (for your information)"))
    b.append(Block("bullets", items=[f"COMPLIANCE: {r.get('marking', '')}"] +
                   [f"COMPLIANCE: {x}" for x in (c.get("runtime") or {}).get("compliance", [])]))
    return fp._numbered(b)


def electronics_rfq_blocks(c: dict[str, Any]) -> list[Block]:
    project: Project = c["project"]
    r = fp._rfq_settings(project)
    tpl_audio = (c.get("audio") or {})
    m = atelier.model(c["params"])
    bb = {k: m.parts[k].bounding_box() for k in ("battery", "driver", "passive_radiator", "main_board")}
    b: list[Block] = fp._header(c, f"Request for quotation: {project.name} speaker electronics, driver and battery")
    b.append(Block("warn", "Values marked UNVERIFIED are design estimates. Items marked COMPLIANCE need certificates from "
                           "an accredited test lab."))
    b.append(Block("h2", "What we would like you to quote"))
    b.append(Block("p", r.get("first_order", "") + " One set = main board, driver, passive radiator, battery pack, sealed "
                   "USB-C receptacle, encoder, status LED and the braided cable. Quantities: "
                   + " / ".join(f"{q:,}" for q in fp.QUANTITY_TIERS) + ". Tell us your MOQ."))
    b.append(Block("h2", "Main board"))
    b.append(Block("bullets", items=[
        "Pre-certified Bluetooth module (state the module and its radio certificates): Bluetooth 5.3 or later, LE Audio "
        "ready; SBC and AAC (aptX Adaptive optional, price it separately); 10 m range in our enclosure.",
        "Multipoint (2 devices), stereo pairing (two speakers), remembers 8 devices, OTA firmware updates; no microphone, "
        "no app.",
        "DSP: bass enhancement, loudness compensation and a limiter, tuned to our enclosure and driver.",
        "20 W RMS Class-D amplifier fed by a boost converter from the 1S battery (about 3.6 V). UNVERIFIED: about 8 A "
        "from the pack at full power; confirm the topology and the cells' rating.",
        "USB-C PD charging 5–9 V up to 20 W; full charge in 3 h or less; play while charging; standby after 20 min.",
        "Knob (rotary encoder with push): turn = volume; press = play/pause; double press = next track; hold 2 s = power; "
        "hold 5 s = pairing; hold 10 s = factory reset.",
        "White status LED: slow pulse when pairing; steady 5 s then off when connected; slow breathing when charging; off "
        "when full; 3 quick blinks when the battery is low.",
        "Plug-in leads for the battery and the USB-C receptacle (the battery is replaceable after removing the base collar).",
        "Antenna: the board sits on the chassis spine near the top, behind the red PC/ABS body (radio-transparent), away "
        "from the steel chassis and gold PVD trim; confirm the 10 m range.",
    ]))
    b.append(Block("h2", "Driver and passive radiator"))
    b.append(Block("bullets", items=[
        "57 mm full-range neodymium driver rated 20 W RMS; send the datasheet with Thiele-Small values, Xmax and its net "
        "displaced volume.",
        "Passive radiator about 60 × 40 mm oval, mass-tunable; tune it with the driver to our box "
        f"(UNVERIFIED: about {tpl_audio.get('box_l', 0.74):.2f} L of air).",
        "Targets: 60 Hz–20 kHz (−6 dB); 90 dB SPL or more at 1 m; THD 1% or less at 85 dB.",
    ]))
    b.append(Block("h2", "Battery pack"))
    b.append(Block("bullets", items=[
        "Pre-certified Li-ion pack: 2 x 18650, 1S2P, about 6,000 mAh / 21.6 Wh, branded cells, protection circuit, plug-in "
        "lead.", "15 h or more at 50% volume (our estimate, UNVERIFIED).",
        "COMPLIANCE: UN38.3 test summary and IEC 62133-2 report for the exact pack.",
    ]))
    b.append(Block("h2", "Other parts in the set"))
    b.append(Block("bullets", items=[
        "Sealed (IP67) mid-mount USB-C receptacle on a small board, with lead and connector (in the base collar).",
        "Rotary encoder with push switch: 24 soft detents, torque 8–12 mNm, press 3–4 N, 0.4 mm travel, 6 mm shaft; 50,000 "
        "presses and 20,000 rotations.",
        "White status LED with a 3 mm light pipe.",
        "Braided USB-C to USB-C cable, 1.5 m, side-angled right-angle plug, in the box (no adapter).",
    ]))
    b.append(Block("h2", "Space available (from our CAD)"))
    sz = lambda k: " × ".join(f"{v:.0f}" for v in (bb[k].size.X, bb[k].size.Y, bb[k].size.Z))  # noqa: E731
    b.append(Block("table", widths=[2.5, 7.5], header=["Item", "Space"], rows=[
        ["Main board", f"{sz('main_board')} mm (W × D × H) on the chassis spine"],
        ["Battery", f"{sz('battery')} mm, upright in the ballast cup, standing on the tray plate"],
        ["Driver", f"Ø{bb['driver'].size.X:.0f} × {bb['driver'].size.Y:.0f} mm deep behind the front grille"],
        ["Passive radiator", f"{bb['passive_radiator'].size.X:.0f} × {bb['passive_radiator'].size.Z:.0f} mm oval, "
                             f"{bb['passive_radiator'].size.Y:.0f} mm including travel, at the rear"],
    ]))
    b.append(Block("h2", "Certification"))
    b.append(Block("bullets", items=[f"COMPLIANCE: {x}" for x in (c.get("runtime") or {}).get("compliance", [])] +
                   ["COMPLIANCE: " + r.get("marking", "")]))
    b += fp._commercial(c)
    b.append(Block("h2", "What to include in your quote"))
    b.append(Block("bullets", items=[
        "Unit price per set at each quantity; NRE for the DSP tuning and firmware; who owns the firmware.",
        "The module's certificates and Bluetooth SIG qualification ID; what product testing you can support.",
        "Datasheets for the module, amplifier, boost converter, charger, cells, driver and radiator.",
        "Lead times for samples and production; warranty; country of origin.",
    ]))
    return fp._numbered(b)


def supplier_bom_csv(c: dict[str, Any]) -> str:
    import csv

    drawn = {pt["cad_key"]: pt for pt in c["parts"]}
    colours = fp._colour_refs(c)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Part no.", "Part", "Qty/speaker", "Material", "Process", "Finish", "Colour reference", "Gloss",
                "Size (mm)", "Supply", "Drawing / STEP", "Notes"])
    for row in c["bom"]["rows"]:
        key = row.get("cad_key")
        item = str(row["item"])
        if key in drawn:
            pt = drawn[key]
            supply, files = "Made to drawing", f"{pt['drawing'].split('/')[-1]}.pdf; {pt['step'].split('/')[-1]}"
            if key == "knob":
                files += f"; artwork/{logo.STEM}.svg / .dxf"
            if key == "collar":
                files += f"; artwork/{LETTERING_STEM}.svg / .dxf"
            notes = "; ".join(["UNVERIFIED: " + u for u in pt["unverified"]] + ["SAFETY: " + x for x in pt["safety"]])
        elif key in ELECTRONIC_PARTS:
            supply, files, notes = "Electronics (separate RFQ)", "", "COMPLIANCE: certified for UK sale (UKCA)"
        else:
            supply, files, notes = "Bought-in", "", row.get("supplier_notes") or ""
        colour, gloss = colours.get(key or "", ("", ""))
        w.writerow([f"A-{int(item):02d}" if item.isdigit() else item, row["name"], f"{row['quantity']:g}", row["material"],
                    row["process"], row["finish"], colour, gloss, row["size_mm"], supply, files, notes])
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Drawings, artwork, checks, the zip
# ---------------------------------------------------------------------------


def drawing_files(c: dict[str, Any], cad_key: str) -> tuple[str, bytes]:
    pt = next((x for x in c["parts"] if x["cad_key"] == cad_key), None)
    if pt is None:
        raise FactoryPackError(f"No made-to-drawing part {cad_key!r}")
    sheet = dr.PartSheet(cad_key, pt["part_no"], pt["name"], pt["material"], pt["process"], pt["finish"], pt["quantity"],
                         c["project"].name, c["cad_version"], c["date"], pt["unverified"], pt["safety"], noun="speaker")
    d = adr.part_drawing(c["params"], sheet)
    return dr.to_svg(d), dr.to_pdf(d)


def collar_lettering_files(params: dict[str, Any]) -> dict[str, bytes]:
    """"ATELIER" as etched under the collar (seen from below, rear at the top), 1:1 SVG and DXF in millimetres."""
    import math

    from build123d import ExportDXF, ExportSVG, Face, Unit, Vector, Wire

    loops = atelier._lettering()
    ys = [q[1] for f in loops for lp in f for q in lp]
    k = atelier.LETTERING_CAP / (max(ys) - min(ys))
    r_text = atelier.model(params).info["collar_lettering_radius"]  # the same circle as the 3D etch

    def ring(q):
        x, y = q[0] * k, q[1] * k
        phi = math.pi / 2 - x / r_text
        return Vector((r_text + y) * math.cos(phi), (r_text + y) * math.sin(phi), 0)

    faces = [Face(Wire.make_polygon([ring(q) for q in f[0]], close=True),
                  [Wire.make_polygon([ring(q) for q in h], close=True) for h in f[1:]]) for f in loops]
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        svg_path, dxf_path = Path(tmp) / f"{LETTERING_STEM}.svg", Path(tmp) / f"{LETTERING_STEM}.dxf"
        svg = ExportSVG(unit=Unit.MM, line_weight=0.05)
        svg.add_layer("lettering_etch", fill_color="black", line_color=None, line_weight=0.0)
        for f in faces:
            svg.add_shape(f, layer="lettering_etch")
        svg.write(str(svg_path))
        dxf = ExportDXF(unit=Unit.MM)
        dxf.add_layer("LETTERING_ETCH")
        for f in faces:
            dxf.add_shape(f, layer="LETTERING_ETCH")
        dxf.write(str(dxf_path))
        out[svg_path.name] = svg_path.read_bytes()
        out[dxf_path.name] = dxf_path.read_bytes()
    return out


def artwork_files(c: dict[str, Any]) -> dict[str, bytes]:
    files = dict(logo.artwork_files(logo.logo_radius(float(c["params"]["knob_diameter"]))))
    files.update(collar_lettering_files(c["params"]))
    return files


_MONEY = re.compile(r"£\s?\d")


def consistency_checks(project: Project, c: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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
    built = atelier.model(c["params"]).parts
    info = model.part_info or {}
    differ = [pt["part_no"] + " " + pt["name"] for pt in c["parts"] if pt["cad_key"] in info and pt["cad_key"] in built
              and abs(built[pt["cad_key"]].volume - info[pt["cad_key"]]["volume_mm3"]) > 0.005 * info[pt["cad_key"]]["volume_mm3"] + 1]
    check("Drawings and STEP files show the same solids", not differ,
          f"CAD v{model.version}: drawings and STEP agree for all {len(c['parts'])} parts" if not differ else
          f"CAD v{model.version} was generated with an older generator ({', '.join(differ)}); regenerate CAD")
    bodies = set(info)
    check("All bodies in the model", set(atelier.PART_KEYS) <= bodies,
          f"{len(bodies)} bodies" + ("" if set(atelier.PART_KEYS) <= bodies else
                                    f"; missing {', '.join(sorted(set(atelier.PART_KEYS) - bodies))}"))
    steps = {o.part_key: o.path for o in model.outputs if o.format == "step" and o.part_key}
    missing = [pt["part_no"] for pt in c["parts"] if pt["cad_key"] not in steps or not (settings.data_dir / steps[pt["cad_key"]]).is_file()]
    check("STEP file for every drawing", not missing,
          f"{len(c['parts'])} drawings, {len(c['parts']) - len(missing)} STEP files" + (f"; missing {missing}" if missing else ""))
    stale = []
    for pt in c["parts"]:
        need = adr.NOTE_PROCESS.get(pt["cad_key"])
        if need and rules.processes[need].name != pt["process"]:
            stale.append(f"{pt['part_no']} {pt['name']}: drawing notes assume {rules.processes[need].name.lower()}, "
                         f"part is {(pt['process'] or 'TBD').lower()}")
    check("Drawing notes match each part's process", not stale, "; ".join(stale) or "all match")
    mism = cad_mismatches(project)
    check("CAD shows every chosen route's design changes", not mism,
          "; ".join(f"{m['part']}: {', '.join(m['changes'])}" for m in mism) or "no mismatches")
    for g in atelier.production_change_checks(c["params"]):
        check(f"Production change: {g['feature']}", g["ok"], g["detail"])
    rows = {r.get("cad_key") for r in c["bom"]["rows"]}
    check("BOM lists every drawn part", all(pt["cad_key"] in rows for pt in c["parts"]), "part numbers A-xx follow the BOM items")
    texts = {"rfq": fp.rfq_markdown(rfq_blocks(c)), "electronics rfq": fp.rfq_markdown(electronics_rfq_blocks(c)),
             "bom.csv": supplier_bom_csv(c)}
    leaks = [name for name, t in texts.items() if _MONEY.search(t)]
    check("No prices or cost targets in supplier documents", not leaks, "clean" if not leaks else f"£ amounts in {leaks}")
    allowed = {ph for _, _, ph in fp.CONTACT_FIELDS}
    found = sorted({m for t in texts.values() for m in re.findall(r"\[[A-Z][A-Z ,]+[^\]]*\]", t)})
    stray = [m for m in found if m not in allowed]
    check("No stray placeholders in the RFQs", not stray,
          ("only the contact fields still blank: " + ", ".join(found) if found else "none") if not stray else
          f"unexpected: {', '.join(stray)}")
    missing_c = fp.missing_contact(project)
    out.append({"check": "Contact and delivery details filled in", "ok": not missing_c, "level": "warn",
                "detail": "all filled in" if not missing_c else
                "empty: " + ", ".join(missing_c) + " (Factory Pack tab); the RFQs show placeholders for them"})
    art = collar_lettering_files(c["params"])
    check("Collar lettering artwork", all(len(v) > 200 for v in art.values()) and len(art) == 2,
          f"{', '.join(sorted(art))}; same loops as the 3D etch")
    open_q = [q["question"] for q in fp.open_questions(project, c) if q["status"] == "open"]
    check("Supplier questions answered", not open_q, "all answered" if not open_q else "; ".join(open_q))
    return out


def readme(c: dict[str, Any]) -> str:
    return "\n".join([
        f"{c['project'].name} rocket Bluetooth speaker: request for quotation pack ({c['date']}, CAD v{c['cad_version']})",
        "",
        "mechanical/   for moulding, metalwork and finishing suppliers:",
        "              rfq.pdf (and rfq.md), drawings/ (PDF + SVG per part), step/ (STEP per part + assembly), bom.csv,",
        "              artwork/ (Bathsheva emblem for the knob, ATELIER lettering for the collar; 1:1 SVG and DXF)",
        "electronics/  for audio electronics, driver and battery suppliers:",
        "              rfq_electronics.pdf (and .md): main board (Bluetooth, DSP, 20 W amplifier, charger), driver,",
        "              passive radiator, pre-certified 1S2P pack, sealed USB-C, encoder, LED, cable",
        "",
        "Quantities to quote: " + ", ".join(f"{q:,}" for q in fp.QUANTITY_TIERS) + " units.",
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
    blocks, eblocks = rfq_blocks(c), electronics_rfq_blocks(c)
    folder = f"{project.slug}_rfq_pack_v{model.version}"
    mech, elec = f"{folder}/mechanical", f"{folder}/electronics"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{folder}/README.txt", readme(c))
        zf.writestr(f"{mech}/rfq.md", fp.rfq_markdown(blocks))
        zf.writestr(f"{mech}/rfq.pdf", fp.rfq_pdf(blocks, MECHANICAL_TITLE))
        zf.writestr(f"{mech}/bom.csv", supplier_bom_csv(c))
        for pt in c["parts"]:
            svg, pdf = drawing_files(c, pt["cad_key"])
            zf.writestr(f"{mech}/{pt['drawing']}.svg", svg)
            zf.writestr(f"{mech}/{pt['drawing']}.pdf", pdf)
            if pt["cad_key"] in steps:
                zf.write(settings.data_dir / steps[pt["cad_key"]], f"{mech}/{pt['step']}")
        if assembly:
            zf.write(settings.data_dir / assembly, f"{mech}/step/{project.slug}_assembly.step")
        for fname, data in artwork_files(c).items():
            zf.writestr(f"{mech}/artwork/{fname}", data)
        zf.writestr(f"{elec}/rfq_electronics.md", fp.rfq_markdown(eblocks))
        zf.writestr(f"{elec}/rfq_electronics.pdf", fp.rfq_pdf(eblocks, ELECTRONICS_TITLE))
    return f"{folder}.zip", buf.getvalue()


def pack_summary(project: Project) -> dict[str, Any]:
    c = pack_contents(project)
    blocks = rfq_blocks(c)
    return {
        "cad_version": c["cad_version"], "ready": c["cad_version"] is not None,
        "parts": [dict(pt) for pt in c["parts"]], "bought_in": c["bought_in"], "hardware": c["hardware"],
        "quantity_tiers": fp.QUANTITY_TIERS, "mass": c["mass"], "brass_parts": [],
        "unverified": [f"{pt['part_no']} {pt['name']}: {u}" for pt in c["parts"] for u in pt["unverified"]],
        "safety": sorted({f"{pt['part_no']} {pt['name']}: {x}" for pt in c["parts"] for x in pt["safety"]}),
        "compliance": [fp._rfq_settings(project).get("marking", ""),
                       *[f"Compliance: {x}" for x in (c.get("runtime") or {}).get("compliance", [])]],
        "runtime": c.get("runtime"), "production_changes": atelier.PRODUCTION_CHANGES,
        "consistency": consistency_checks(project, c) if c["cad_version"] is not None else [],
        "open_questions": fp.open_questions(project, c), "placeholders": fp.placeholders(project),
        "contact": fp.contact(project),
        "contact_fields": [{"key": k, "label": label, "placeholder": ph} for k, label, ph in fp.CONTACT_FIELDS],
        "missing_contact": fp.missing_contact(project),
        "rfq_markdown": fp.rfq_markdown(blocks), "electronics_rfq_markdown": fp.rfq_markdown(electronics_rfq_blocks(c)),
        "notes": ["Our cost estimates and targets are not included in anything sent to suppliers.",
                  "The zip has two folders: mechanical/ for moulding, metalwork and finishing suppliers, electronics/ for "
                  "the audio electronics, driver and battery suppliers."],
    }

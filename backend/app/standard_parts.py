"""Standard off-the-shelf parts library and product concepts, read from `standard-parts/*.md`. Pure.

The two markdown files at the repo root are the source of truth and stay readable by people:

- `library.md`: `## N. Category` / `### N.M Subcategory` headings, each with one table of parts
  (Part | Material | Sizes | Supplier & link | Unit price | Price breaks | MOQ | Finish / quality).
- `product-ideas.md`: a summary table (retail price per concept) and one `### N. Name — subtitle` section
  per concept with bold-labelled bullets. Each concept carries a hidden parts list in an HTML comment
  (`<!-- concept-parts` ... `-->`, a YAML list of `{part, qty or sizes, note, option}`), so it can be costed and
  opened in the concept builder.

A part's id is `slug(part name)--slug(supplier)`. Quantities are in the part's priced unit: 0.16 of a
£20 sheet, 0.25 of a 1 m tube. Prices are read from the "Unit price" cell: the first £, € or $ figure,
plus any further figure with its own label in brackets ("£5.00 (sample); £20.00 (250 × 250 mm)"), which
a concept line can pick as `option`;
EUR and USD are converted at `FX`. Price breaks ("£0.75 per tube at 100+") apply when the order quantity
(build quantity × quantity per product) reaches the break. Nothing here reads the database.

Tube, rod, bar, strip and sheet parts also have a priced unit in mm, from the hidden `<!-- priced-units`
block at the end of library.md (a length, or a width × height). A concept line for one of these can give
`length_mm`, or `width_mm` and `height_mm`, with `count` and `waste_pct`, instead of a fraction: the
fraction is count × length / unit length (or × area / unit area) × (1 + waste %), so the cost is the same as
entering that fraction directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.datadir import BACKEND_DIR

LIBRARY_DIR = BACKEND_DIR.parent / "standard-parts"
LIBRARY_FILE = "library.md"
IDEAS_FILE = "product-ideas.md"

# Conversion to GBP. EUR as in product-ideas.md; USD as in seed/cost/bought_in.yaml (GBP/USD 1.3224, Oct 2026).
FX = {"GBP": 1.0, "EUR": 0.85, "USD": round(1 / 1.3224, 4)}
QUANTITIES = (100, 500)
# Parts cost as a share of the DTC factory-cost target: below ROOM leaves room for labour; above 1 is over.
ROOM = 0.75

_PRICE = r"(US \$|£|€|\$)\s?(\d[\d,]*(?:\.\d+)?)"
_PRICE_RE = re.compile(_PRICE)
_BREAK_RE = re.compile(_PRICE + r"[^£€$|]*?\bat (\d[\d,]*)\+?")
# A figure followed (after an optional "ex VAT" / "inc VAT") by a parenthesised label: one priced variant.
_LABEL_RE = re.compile(r"\s*(?:(?:ex|inc)\.? VAT\s*)?\(([^)]*)\)")
_AVAILABILITY = ("discontinued", "no longer", "out of stock", "not stocked", "end of life")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_CURRENCY = {"£": "GBP", "€": "EUR", "$": "USD", "US $": "USD"}


class LibraryError(ValueError):
    """The markdown doesn't have the expected structure."""


@dataclass
class PriceBreak:
    quantity: float
    price: float
    currency: str

    @property
    def price_gbp(self) -> float:
        return self.price * FX[self.currency]


@dataclass
class PriceOption:
    """One priced variant in a part's "Unit price" cell, e.g. "£20.00 ex VAT (250 × 250 mm mill)"."""

    price: float
    currency: str
    label: str

    @property
    def price_gbp(self) -> float:
        return self.price * FX[self.currency]


@dataclass
class LibraryPart:
    id: str
    category: str  # "1. Tubes"
    subcategory: str  # "1.3 Brass tube"
    name: str
    material: str
    sizes: str
    supplier: str
    supplier_cell: str
    links: list[dict[str, str]]
    # Files in the repo the entry comes from instead of a web page, e.g. a supplier's price list export
    # (`standard-parts/price-lists/...csv`), written in backticks in the supplier cell.
    source_files: list[str]
    price_text: str
    price_status: str  # listed | quote | not_shown
    price: float | None
    currency: str | None
    options: list[PriceOption]  # the first is `price`; a concept line picks one by index
    price_from: bool  # "From £x" / a range: the figure is the cheapest option
    price_uncertain: bool  # the listing says to confirm or the currency is unclear
    breaks_text: str
    breaks: list[PriceBreak]
    moq: str
    note: str
    availability: str  # non-empty when the listing or note says discontinued / out of stock
    # Per price variant: {"length_mm": L} or {"width_mm": W, "height_mm": H}, or None (priced per piece/pack).
    units: list[dict[str, float] | None] = field(default_factory=list)

    @property
    def price_gbp(self) -> float | None:
        return None if self.price is None else self.price * FX[self.currency or "GBP"]

    def unit_price_gbp(self, order_quantity: float, option: int = 0) -> float | None:
        """GBP per priced unit. Price breaks belong to the first (headline) price only."""
        if not self.options:
            return None
        if option:
            return self.options[min(option, len(self.options) - 1)].price_gbp
        price = self.price_gbp
        for b in sorted(self.breaks, key=lambda b: b.quantity):
            if order_quantity >= b.quantity:
                price = b.price_gbp
        return price

    def unit(self, option: int = 0) -> dict[str, float] | None:
        """The priced unit in mm for a variant, or None when the part is priced per piece or pack."""
        if not self.units:
            return None
        return self.units[min(max(option, 0), len(self.units) - 1)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "category": self.category, "subcategory": self.subcategory, "name": self.name,
            "material": self.material, "sizes": self.sizes, "supplier": self.supplier,
            "supplier_cell": self.supplier_cell, "links": self.links, "source_files": self.source_files,
            "price_text": self.price_text,
            "price_status": self.price_status, "price": self.price, "currency": self.currency,
            "options": [{"price": o.price, "currency": o.currency, "label": o.label,
                         "price_gbp": round(o.price_gbp, 4)} for o in self.options],
            "price_gbp": None if self.price_gbp is None else round(self.price_gbp, 4),
            "price_from": self.price_from, "price_uncertain": self.price_uncertain,
            "breaks_text": self.breaks_text,
            "breaks": [{"quantity": b.quantity, "price": b.price, "currency": b.currency,
                        "price_gbp": round(b.price_gbp, 4)} for b in self.breaks],
            "moq": self.moq, "note": self.note, "availability": self.availability, "units": self.units,
        }


@dataclass
class Subsection:
    number: str
    title: str
    parts: list[LibraryPart] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class Section:
    number: str
    title: str
    subsections: list[Subsection] = field(default_factory=list)


@dataclass
class Library:
    sections: list[Section]
    about: list[dict[str, Any]]  # unnumbered sections ("How to read this", "Gaps and next steps")

    @property
    def parts(self) -> dict[str, LibraryPart]:
        return {p.id: p for s in self.sections for sub in s.subsections for p in sub.parts}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c)


def _amount(text: str) -> float:
    return float(text.replace(",", ""))


def parse_price(cell: str) -> dict[str, Any]:
    low = cell.lower()
    uncertain = any(w in low for w in ("unclear", "confirm", "check"))
    matches = list(_PRICE_RE.finditer(cell))
    if not matches:
        status = "quote" if "quote only" in low else "not_shown"
        return {"price_status": status, "price": None, "currency": None, "options": [], "price_from": False,
                "price_uncertain": uncertain}
    first = matches[0]
    options = []
    for i, m in enumerate(matches):
        label = _LABEL_RE.match(cell, m.end())
        if i == 0:
            options.append(PriceOption(_amount(m.group(2)), _CURRENCY[m.group(1)], label.group(1) if label else ""))
        elif label and not re.search(r"[–-]\s*$", cell[: m.start()]) and not cell[: m.start()].rstrip().endswith("("):
            # A labelled figure that isn't the top of a range ("£2–£9 (x)") or inside another label.
            if cell[: m.start()].count("(") == cell[: m.start()].count(")"):
                options.append(PriceOption(_amount(m.group(2)), _CURRENCY[m.group(1)], label.group(1)))
    rest = cell[first.end():]
    return {
        "price_status": "listed",
        "price": options[0].price,
        "currency": options[0].currency,
        "options": options,
        "price_from": ("from" in cell[: first.start()].lower()
                       or bool(re.match(r"\s?[–-]\s?(US \$|£|€|\$)", rest))
                       or bool(re.search(r"\bto (US \$|£|€|\$)", rest))),
        "price_uncertain": uncertain,
    }


def parse_breaks(cell: str) -> list[PriceBreak]:
    return [PriceBreak(quantity=_amount(m.group(3)), price=_amount(m.group(2)), currency=_CURRENCY[m.group(1)])
            for m in _BREAK_RE.finditer(cell)]


def _availability(text: str) -> str:
    low = text.lower()
    hits = [w for w in _AVAILABILITY if w in low]
    return "; ".join(hits)


def _part(cells: list[str], category: str, subcategory: str) -> LibraryPart:
    if len(cells) != 8:
        raise LibraryError(f"{subcategory}: expected 8 columns, got {len(cells)}: {cells[:1]}")
    name, material, sizes, supplier_cell, price_text, breaks_text, moq, note = cells
    supplier = supplier_cell.split(" — ")[0] if " — " in supplier_cell else _LINK_RE.sub(r"\1", supplier_cell)
    links = [{"label": label, "url": url} for label, url in _LINK_RE.findall(supplier_cell)]
    source_files = re.findall(r"`(standard-parts/[^`]+)`", supplier_cell)
    return LibraryPart(
        id=f"{slug(name)}--{slug(supplier)}", category=category, subcategory=subcategory, name=name,
        material=material, sizes=sizes, supplier=supplier.strip(), supplier_cell=supplier_cell, links=links,
        source_files=source_files,
        price_text=price_text, breaks_text=breaks_text, breaks=parse_breaks(breaks_text), moq=moq, note=note,
        availability=_availability(f"{price_text} {note} {moq}"),
        **parse_price(price_text),
    )


_UNITS_RE = re.compile(r"^<!-- priced-units\n(.*?)^-->\n?", re.S | re.M)


def _unit(value: Any, where: str) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) not in ({"length_mm"}, {"width_mm", "height_mm"}):
        raise LibraryError(f"priced-units {where}: give length_mm, or width_mm and height_mm")
    out = {k: float(v) for k, v in value.items()}
    if any(v <= 0 for v in out.values()):
        raise LibraryError(f"priced-units {where}: sizes must be positive")
    return out


def _apply_units(block: str, parts: dict[str, LibraryPart]) -> None:
    for part_id, value in (yaml.safe_load(block) or {}).items():
        part = parts.get(part_id)
        if part is None:
            raise LibraryError(f"priced-units: unknown part {part_id}")
        if isinstance(value, list):
            if len(value) != len(part.options):
                raise LibraryError(
                    f"priced-units {part_id}: {len(value)} entries for {len(part.options)} price variants")
            part.units = [None if v is None else _unit(v, part_id) for v in value]
        else:
            part.units = [_unit(value, part_id)] * max(len(part.options), 1)


def parse_library(text: str) -> Library:
    units = _UNITS_RE.search(text)
    text = _UNITS_RE.sub("", text)
    sections: list[Section] = []
    about: list[dict[str, Any]] = []
    section: Section | None = None
    sub: Subsection | None = None
    about_block: dict[str, Any] | None = None
    header_seen = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            title = line[3:].strip()
            m = re.match(r"(\d+)\.\s+(.+)", title)
            sub = None
            if m:
                section, about_block = Section(m.group(1), m.group(2)), None
                sections.append(section)
            else:
                section, about_block = None, {"title": title, "lines": []}
                about.append(about_block)
            continue
        if line.startswith("### "):
            m = re.match(r"(\d+\.\d+)\s+(.+)", line[4:].strip())
            if section is None or m is None:
                raise LibraryError(f"subsection outside a numbered section: {line}")
            sub = Subsection(m.group(1), m.group(2))
            section.subsections.append(sub)
            header_seen = False
            continue
        if about_block is not None:
            if line.strip() and line.strip() != "---":
                about_block["lines"].append(line)
            continue
        if sub is None or section is None:
            continue
        if line.startswith("|"):
            cells = _cells(line)
            if _is_separator(cells):
                continue
            if not header_seen:
                header_seen = True  # the column header row
                continue
            sub.parts.append(_part(cells, f"{section.number}. {section.title}", f"{sub.number} {sub.title}"))
        elif line.strip() and line.strip() != "---":
            sub.notes.append(line.strip())
    library = Library(sections, about)
    ids = [p.id for s in sections for su in s.subsections for p in su.parts]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise LibraryError(f"duplicate part ids: {dupes}")
    if units:
        _apply_units(units.group(1), library.parts)
    return library


# ---------------------------------------------------------------------------
# Costing
# ---------------------------------------------------------------------------


def factory_target(retail_inc_vat: float | None, vat_rate: float, dtc_share: float) -> float | None:
    if not retail_inc_vat:
        return None
    return retail_inc_vat / (1 + vat_rate) * dtc_share


def verdict(share: float | None) -> str | None:
    if share is None:
        return None
    return "room" if share < ROOM else ("tight" if share <= 1 else "over")


DIM_KEYS = ("length_mm", "width_mm", "height_mm", "count", "waste_pct")


def line_quantity(line: dict[str, Any], part: LibraryPart | None, option: int) -> tuple[float, str, str]:
    """(quantity in priced units, entry mode, problem) for a concept line.

    Mode "length" or "area" when the line gives sizes in mm that match the part's priced unit; otherwise
    "units" and the line's own `quantity`. A size that doesn't fit the part (a length for a sheet, or a part
    priced per piece) falls back to `quantity` and says so.
    """
    has_length = line.get("length_mm") is not None
    has_area = line.get("width_mm") is not None or line.get("height_mm") is not None
    if not (has_length or has_area):
        return float(line.get("quantity") or 0), "units", ""
    unit = part.unit(option) if part is not None else None
    count = float(line.get("count") if line.get("count") is not None else 1)
    allowance = 1 + float(line.get("waste_pct") or 0) / 100
    if unit and has_length and "length_mm" in unit:
        return count * float(line["length_mm"]) / unit["length_mm"] * allowance, "length", ""
    if unit and has_area and "width_mm" in unit:
        w, h = float(line.get("width_mm") or 0), float(line.get("height_mm") or 0)
        return count * w * h / (unit["width_mm"] * unit["height_mm"]) * allowance, "area", ""
    problem = ("this part is priced per piece or pack, not by size" if unit is None
               else f"this part is priced by {'length' if 'length_mm' in unit else 'width × height'}")
    return float(line.get("quantity") or 0), "units", problem


def cost_lines(lines: list[dict[str, Any]], parts: dict[str, LibraryPart], retail_price: float | None,
               vat_rate: float, dtc_share: float) -> dict[str, Any]:
    """Parts cost of a concept at each of QUANTITIES, line by line, against the DTC factory-cost target.

    `lines`: [{"part_id", "quantity", "note"?, "option"?, sizes?}]; `option` picks one of the part's priced
    variants (default the first); sizes (`DIM_KEYS`, see `line_quantity`) replace `quantity` for parts with a
    priced unit in mm. Lines with an unknown part or no listed price count £0 and are reported, so the
    total is a floor.
    """
    out_lines = []
    totals = {q: 0.0 for q in QUANTITIES}
    for line in lines:
        option = int(line.get("option") or 0)
        part = parts.get(line["part_id"])
        if part is not None and part.options:
            option = min(max(option, 0), len(part.options) - 1)
        qty, mode, problem = line_quantity(line, part, option)
        row: dict[str, Any] = {"part_id": line["part_id"], "quantity": round(qty, 6), "note": line.get("note", ""),
                               "option": option, "mode": mode, "size_problem": problem,
                               "unit_size": part.unit(option) if part is not None else None,
                               **{k: line.get(k) for k in DIM_KEYS},
                               "known": part is not None, "priced": part is not None and part.price is not None}
        for q in QUANTITIES:
            unit = part.unit_price_gbp(qty * q, option) if part is not None else None
            cost = (unit or 0.0) * qty
            totals[q] += cost
            row[f"unit_{q}"] = None if unit is None else round(unit, 4)
            row[f"cost_{q}"] = round(cost, 4)
            row[f"break_{q}"] = part is not None and unit is not None and option == 0 and unit != part.price_gbp
        out_lines.append(row)
    target = factory_target(retail_price, vat_rate, dtc_share)
    result: dict[str, Any] = {
        "lines": out_lines,
        "retail_price": retail_price,
        "target": None if target is None else round(target, 2),
        "unpriced": [r["part_id"] for r in out_lines if r["known"] and not r["priced"]],
        "unknown": [r["part_id"] for r in out_lines if not r["known"]],
    }
    for q in QUANTITIES:
        share = None if not target else totals[q] / target
        result[f"total_{q}"] = round(totals[q], 2)
        result[f"share_{q}"] = None if share is None else round(share, 4)
        result[f"verdict_{q}"] = verdict(share)
    return result


# ---------------------------------------------------------------------------
# Concepts (product-ideas.md)
# ---------------------------------------------------------------------------


@dataclass
class SeedConcept:
    number: int
    key: str
    name: str
    subtitle: str
    group: str
    description: str
    retail_price: float | None
    library_parts: list[str]
    custom_work: str
    parts_cost_text: str
    stated_cost: dict[int, float]
    not_in_library: str
    main_risk: str
    lines: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number, "key": self.key, "name": self.name, "subtitle": self.subtitle,
            "group": self.group, "description": self.description, "retail_price": self.retail_price,
            "library_parts": self.library_parts, "custom_work": self.custom_work,
            "parts_cost_text": self.parts_cost_text,
            "stated_cost": {str(k): v for k, v in self.stated_cost.items()},
            "not_in_library": self.not_in_library, "main_risk": self.main_risk, "lines": self.lines,
        }


_BULLET_RE = re.compile(r"^- \*\*(.+?):\*\*\s*(.*)$")
_STATED_RE = re.compile(r"£([\d,]+(?:\.\d+)?)(?: per \w+)? at 100 and £([\d,]+(?:\.\d+)?) at 500")


def _retail_prices(text: str) -> dict[int, float]:
    out: dict[int, float] = {}
    in_summary = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_summary = line.strip() == "## Summary"
            continue
        if in_summary and line.startswith("|"):
            cells = _cells(line)
            if cells and cells[0].isdigit():
                m = re.search(r"£([\d,]+)", cells[3])
                if m:
                    out[int(cells[0])] = _amount(m.group(1))
    return out


def _seed_line(p: dict[str, Any]) -> dict[str, Any]:
    """A concept-parts entry: {part, qty | length_mm | size_mm: [w, h], count?, waste_pct?, note?, option?}."""
    line: dict[str, Any] = {"part_id": str(p["part"]), "quantity": float(p.get("qty", 0)),
                            "note": str(p.get("note", "")), "option": int(p.get("option", 0))}
    if "length_mm" in p:
        line["length_mm"] = float(p["length_mm"])
    if "size_mm" in p:
        line["width_mm"], line["height_mm"] = (float(v) for v in p["size_mm"])
    if "length_mm" in p or "size_mm" in p:
        line["count"] = float(p.get("count", 1))
        line["waste_pct"] = float(p.get("waste_pct", 0))
    return line


def parse_concepts(text: str) -> list[SeedConcept]:
    retail = _retail_prices(text)
    concepts: list[SeedConcept] = []
    group = ""
    current: dict[str, Any] | None = None
    in_comment = False

    def finish() -> None:
        if current is None:
            return
        b = current["bullets"]
        stated = {}
        m = _STATED_RE.search(b.get("Parts cost", {}).get("text", ""))
        if m:
            stated = {100: _amount(m.group(1)), 500: _amount(m.group(2))}
        lines = [_seed_line(p) for p in (yaml.safe_load("\n".join(current["parts_yaml"])) or [])]
        concepts.append(SeedConcept(
            number=current["number"], key=slug(current["name"]), name=current["name"],
            subtitle=current["subtitle"], group=current["group"], description=" ".join(current["description"]),
            retail_price=retail.get(current["number"]),
            library_parts=b.get("Library parts", {}).get("items", []),
            custom_work=b.get("Custom work", {}).get("text", ""),
            parts_cost_text=b.get("Parts cost", {}).get("text", ""), stated_cost=stated,
            not_in_library=b.get("Not in library", {}).get("text", ""),
            main_risk=b.get("Main risk", {}).get("text", ""), lines=lines,
        ))

    for raw in text.splitlines():
        line = raw.rstrip()
        if in_comment:
            if line.strip() == "-->":
                in_comment = False
            elif current is not None:
                current["parts_yaml"].append(line)
            continue
        if line.strip() == "<!-- concept-parts":
            in_comment = True
            continue
        if line.startswith("## "):
            finish()
            current = None
            group = line[3:].strip()
            continue
        if line.startswith("### "):
            finish()
            m = re.match(r"(\d+)\.\s+(.+?)\s+—\s+(.+)", line[4:].strip())
            current = None if m is None else {
                "number": int(m.group(1)), "name": m.group(2), "subtitle": m.group(3), "group": group,
                "description": [], "bullets": {}, "last": None, "parts_yaml": [],
            }
            continue
        if current is None or not line.strip() or line.strip() == "---":
            continue
        bm = _BULLET_RE.match(line)
        if bm:
            current["last"] = bm.group(1)
            current["bullets"][bm.group(1)] = {"text": bm.group(2), "items": []}
        elif line.startswith("  - ") and current["last"]:
            current["bullets"][current["last"]]["items"].append(line[4:].strip().rstrip(";."))
        elif line.startswith("  ") and current["last"]:
            current["bullets"][current["last"]]["text"] += " " + line.strip()
        elif not current["bullets"]:
            current["description"].append(line.strip())
    finish()
    return concepts


# ---------------------------------------------------------------------------
# Loading from disk
# ---------------------------------------------------------------------------


def load_library(directory: Path = LIBRARY_DIR) -> Library:
    """Parsed fresh on each call (the files are small), so edits to the markdown show without a restart."""
    return parse_library((directory / LIBRARY_FILE).read_text(encoding="utf-8"))


def load_concepts(directory: Path = LIBRARY_DIR) -> list[SeedConcept]:
    return parse_concepts((directory / IDEAS_FILE).read_text(encoding="utf-8"))

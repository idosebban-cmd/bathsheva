"""Standard parts library and concepts (standard-parts/*.md), the cost calculation and the concepts API."""

from __future__ import annotations

import pytest

from app import standard_parts as sp

LIB = sp.load_library()
PARTS = LIB.parts
CONCEPTS = sp.load_concepts()


def test_library_parses_every_category():
    assert [s.title for s in LIB.sections] == [
        "Tubes", "Domes, caps and cones", "Lighting hardware", "Brass and metal details", "Grilles and mesh",
        "Turned and wooden parts", "Audio and electronics",
    ]
    assert all(sub.parts for s in LIB.sections for sub in s.subsections)
    assert len(PARTS) > 150
    assert {a["title"] for a in LIB.about} == {"How to read this", "Gaps and next steps"}


def test_every_part_has_supplier_link_and_price_status():
    root = sp.LIBRARY_DIR.parent
    for p in PARTS.values():
        assert p.supplier and (p.links or p.source_files), p.id
        for f in p.source_files:
            assert (root / f).is_file(), f"{p.id}: {f} is not in the repo"
        assert p.price_status in {"listed", "quote", "not_shown"}
        assert (p.price is not None) == (p.price_status == "listed"), p.id


def test_price_statuses_follow_the_file():
    assert PARTS["custom-trade-cylinders--j-moncrieff-uk"].price_status == "quote"
    assert PARTS["small-opal-dome-55-mm-fitter-neck--j-moncrieff-uk"].price_status == "not_shown"
    # A figure without a currency is not a price.
    assert PARTS["e27-shade-ring--urban-cottage-industries-uk"].price_status == "not_shown"


def test_price_parsing():
    assert sp.parse_price("£4.99 ex VAT / £5.99 inc VAT per pack of 10")["price"] == 4.99
    r = sp.parse_price("€24.95 (listed €20.62 ex VAT)")
    assert (r["price"], r["currency"], len(r["options"])) == (24.95, "EUR", 1)
    r = sp.parse_price("£5.00 ex VAT (45 mm polished sample); £20.00 ex VAT (250 × 250 mm mill)")
    assert [(o.price, o.label) for o in r["options"]] == [(5.0, "45 mm polished sample"), (20.0, "250 × 250 mm mill")]
    # The top of a range is not a separate option.
    r = sp.parse_price("£2.29–£10.65 ex VAT (1.2 mm wall)")
    assert len(r["options"]) == 1 and r["price_from"]
    assert sp.parse_price("From £1.76 (category floor price)")["price_from"]
    assert sp.parse_price("Quote only")["price_status"] == "quote"


def test_price_breaks():
    (b,) = sp.parse_breaks("£0.75 per tube at 100+")
    assert (b.quantity, b.price) == (100, 0.75)
    assert sp.parse_breaks("£32.95 per pack of 10") == []
    tube = PARTS["postal-tubes-with-end-caps-raja--morplan-uk"]
    assert tube.unit_price_gbp(99) == 1.07 and tube.unit_price_gbp(100) == 0.75
    # A break belongs to the headline price only, not to another variant.
    sheet = PARTS["brass-sheet-sample-small-sheet--the-metal-store-uk"]
    assert sheet.unit_price_gbp(1000, option=1) == 20.0


def test_eur_converted_at_fx():
    driver = PARTS["visaton-frs-8-8--toutlehautparleur-tlhp-france"]
    assert driver.price_gbp == pytest.approx(12.56 * sp.FX["EUR"])


def test_availability_flags():
    assert "discontinued" in PARTS["solid-brass-gold-plated-knob-25-mm--hificollective-uk"].availability
    assert "out of stock" in PARTS["brass-tube-10-mm-od-1-m--lampfix-uk"].availability
    assert PARTS["internally-frosted-cylinder-shade--j-moncrieff-uk"].availability == ""
    # A supplier that stopped stocking a part that is still made: out of stock there, not discontinued.
    cpc = PARTS["visaton-frs-8-m-8--cpc-farnell-uk"].availability
    assert "not stocked" in cpc and "no longer" not in cpc and "discontinued" not in cpc
    assert PARTS["visaton-frs-8-m-8-2001--sos-electronic-eu"].availability == ""


def test_fifteen_concepts_with_all_fields():
    assert [c.number for c in CONCEPTS] == list(range(1, 16))
    for c in CONCEPTS:
        assert c.description and c.library_parts and c.custom_work and c.main_risk, c.name
        assert c.retail_price and 150 <= c.retail_price <= 250, c.name
        assert c.lines, f"{c.name}: no concept-parts block"


def test_concept_parts_exist_and_avoid_unavailable_parts():
    for c in CONCEPTS:
        for line in c.lines:
            part = PARTS.get(line["part_id"])
            assert part is not None, f"{c.name}: unknown part {line['part_id']}"
            assert part.price is not None, f"{c.name}: {part.id} has no listed price"
            assert not part.availability, f"{c.name}: {part.id} is {part.availability}"


@pytest.mark.parametrize("concept", CONCEPTS, ids=lambda c: c.key)
def test_concept_costs_match_the_stated_costs(concept):
    """The hidden parts list reproduces the parts cost written in product-ideas.md."""
    r = sp.cost_lines(concept.lines, PARTS, concept.retail_price, 0.2, 0.33)
    assert concept.stated_cost, concept.name
    assert r["total_100"] == pytest.approx(concept.stated_cost[100], abs=0.02)
    assert r["total_500"] == pytest.approx(concept.stated_cost[500], abs=0.02)
    assert not r["unpriced"] and not r["unknown"]


def test_cost_against_target():
    lines = [{"part_id": "internally-frosted-cylinder-shade--j-moncrieff-uk", "quantity": 1}]
    r = sp.cost_lines(lines, PARTS, 240, 0.2, 0.33)
    assert r["target"] == pytest.approx(66.0)
    assert r["total_100"] == 35.0 and r["verdict_100"] == "room"
    assert sp.cost_lines(lines, PARTS, 60, 0.2, 0.33)["verdict_100"] == "over"
    assert sp.cost_lines(lines, PARTS, None, 0.2, 0.33)["target"] is None


def test_unknown_and_unpriced_lines_count_zero():
    lines = [{"part_id": "custom-trade-cylinders--j-moncrieff-uk", "quantity": 2}, {"part_id": "gone", "quantity": 1}]
    r = sp.cost_lines(lines, PARTS, 200, 0.2, 0.33)
    assert r["total_100"] == 0
    assert r["unpriced"] == ["custom-trade-cylinders--j-moncrieff-uk"] and r["unknown"] == ["gone"]


def test_library_markdown_structure_errors():
    with pytest.raises(sp.LibraryError):
        sp.parse_library("## 1. A\n\n### 1.1 B\n\n| a | b |\n|---|---|\n| x | y |\n")


# --- API ---------------------------------------------------------------------


def test_library_api(client):
    r = client.get("/api/standard-parts")
    assert r.status_code == 200
    body = r.json()
    assert len(body["sections"]) == 7
    assert body["pricing"] == {"vat_rate": 0.2, "dtc_factory_share": 0.33}
    part = body["sections"][0]["subsections"][0]["parts"][0]
    assert {"name", "material", "sizes", "supplier", "links", "price_text", "price_status", "moq"} <= set(part)


def test_seed_concepts_api(client):
    body = client.get("/api/standard-parts/concepts").json()
    assert len(body) == 15
    tambour = body[0]
    assert tambour["name"] == "Tambour" and tambour["cost"]["total_100"] == 64.84


def test_cost_api(client):
    r = client.post("/api/standard-parts/cost", json={
        "retail_price": 150, "lines": [{"part_id": "bun-feet--cousins-uk", "quantity": 4}]})
    assert r.status_code == 200
    assert r.json()["total_500"] == 14.0 and r.json()["target"] == 41.25


def test_concepts_crud(client):
    body = {"name": "Desk lamp", "retail_price": 180, "based_on": "bell",
            "lines": [{"part_id": "bun-feet--cousins-uk", "quantity": 3, "note": "feet"}]}
    r = client.post("/api/concepts", json=body)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert r.json()["cost"]["total_100"] == 10.5
    assert r.json()["created_at"].endswith("Z")

    body["lines"].append({"part_id": "solid-brass-ball-finial-7112--in-the-light-direction-uk", "quantity": 1})
    r = client.put(f"/api/concepts/{cid}", json=body)
    assert r.status_code == 200 and r.json()["cost"]["total_100"] == 11.5

    listed = client.get("/api/concepts").json()
    assert [c["id"] for c in listed] == [cid] and listed[0]["based_on"] == "bell"

    assert client.post("/api/concepts", json={**body, "lines": [{"part_id": "nope", "quantity": 1}]}).status_code == 422
    assert client.post("/api/concepts", json={**body, "name": ""}).status_code == 422

    assert client.delete(f"/api/concepts/{cid}").status_code == 204
    assert client.get(f"/api/concepts/{cid}").status_code == 404


# --- Sizes in mm -------------------------------------------------------------


def test_priced_units_cover_tube_rod_bar_and_sheet_parts():
    sized = {pid: p for pid, p in PARTS.items() if p.units}
    assert len(sized) >= 20
    assert PARTS["cz108-round-tube-polished--the-metal-store-uk"].unit() == {"length_mm": 2500}
    sheet = PARTS["brass-sheet-sample-small-sheet--the-metal-store-uk"]
    assert sheet.unit(0) == {"width_mm": 45, "height_mm": 45} and sheet.unit(1) == {"width_mm": 250, "height_mm": 250}
    # Every sized part has a listed price, and pieces (finished cylinders, kits) are not sized.
    assert all(p.price is not None for p in sized.values())
    assert PARTS["internally-frosted-cylinder-shade--j-moncrieff-uk"].unit() is None


def test_priced_units_block_is_validated():
    table = "## 1. A\n\n### 1.1 B\n\n| a | b | c | d | e | f | g | h |\n|---|---|---|---|---|---|---|---|\n" \
            "| Tube | Brass | 1 m | S, UK — [l](https://x.uk) | £10 | — | 1 | — |\n"
    ok = sp.parse_library(table + "\n<!-- priced-units\ntube--s-uk: {length_mm: 1000}\n-->\n")
    assert ok.parts["tube--s-uk"].unit() == {"length_mm": 1000}
    for bad in ("nope--s-uk: {length_mm: 1000}", "tube--s-uk: {width_mm: 10}", "tube--s-uk: {length_mm: 0}",
                "tube--s-uk: [{length_mm: 1}, {length_mm: 2}]"):
        with pytest.raises(sp.LibraryError):
            sp.parse_library(table + f"\n<!-- priced-units\n{bad}\n-->\n")


def test_length_and_area_convert_to_the_same_cost_as_the_fraction():
    tube = "cz108-round-tube-polished--the-metal-store-uk"  # £60 per 2.5 m
    by_mm = sp.cost_lines([{"part_id": tube, "length_mm": 300, "count": 2}], PARTS, None, 0.2, 0.33)
    by_fraction = sp.cost_lines([{"part_id": tube, "quantity": 0.24}], PARTS, None, 0.2, 0.33)
    assert by_mm["lines"][0]["mode"] == "length" and by_mm["lines"][0]["quantity"] == pytest.approx(0.24)
    assert by_mm["total_100"] == by_fraction["total_100"] == 14.4

    ply = "premium-beech-plywood-18-mm-glue-class-3--cts-diy-uk"  # £48.82 per 2440 × 1220
    line = {"part_id": ply, "width_mm": 1220, "height_mm": 610, "count": 2, "waste_pct": 10}
    r = sp.cost_lines([line], PARTS, None, 0.2, 0.33)
    assert r["lines"][0]["mode"] == "area" and r["lines"][0]["quantity"] == pytest.approx(0.55)
    assert r["total_500"] == pytest.approx(48.82 * 0.55, abs=0.01)


def test_size_follows_the_price_variant():
    """The same 100 × 100 mm piece is a different fraction of the 45 mm sample and the 250 mm sheet."""
    sheet = "brass-sheet-sample-small-sheet--the-metal-store-uk"
    big = sp.cost_lines([{"part_id": sheet, "width_mm": 100, "height_mm": 100, "option": 1}], PARTS, None, 0.2, 0.33)
    assert big["lines"][0]["quantity"] == pytest.approx(0.16) and big["total_100"] == 3.2


def test_sizes_on_a_part_priced_per_piece_fall_back_to_the_quantity():
    r = sp.cost_lines([{"part_id": "bun-feet--cousins-uk", "length_mm": 100, "quantity": 3}], PARTS, None, 0.2, 0.33)
    row = r["lines"][0]
    assert row["mode"] == "units" and row["quantity"] == 3 and "per piece" in row["size_problem"]
    r = sp.cost_lines([{"part_id": "cz108-round-tube-polished--the-metal-store-uk", "width_mm": 10, "height_mm": 10,
                        "quantity": 1}], PARTS, None, 0.2, 0.33)
    assert r["lines"][0]["mode"] == "units" and "length" in r["lines"][0]["size_problem"]


def test_concepts_give_sizes_in_mm_where_the_part_is_sized():
    lune = next(c for c in CONCEPTS if c.key == "lune")
    ply = next(ln for ln in lune.lines if ln["part_id"].startswith("premium-beech-plywood"))
    assert (ply["width_mm"], ply["height_mm"], ply["count"], ply["waste_pct"]) == (160, 160, 3, 30)
    for c in CONCEPTS:
        for ln in c.lines:
            if "length_mm" in ln or "width_mm" in ln:
                assert sp.line_quantity(ln, PARTS[ln["part_id"]], ln["option"])[1] != "units", (c.name, ln["part_id"])


def test_concept_api_keeps_sizes(client):
    tube = "cz108-round-tube-polished--the-metal-store-uk"
    body = {"name": "Stem", "lines": [{"part_id": tube, "length_mm": 250, "count": 1, "note": "stem"}]}
    r = client.post("/api/concepts", json=body)
    assert r.status_code == 201, r.text
    line = r.json()["lines"][0]
    assert line["length_mm"] == 250 and line["quantity"] == pytest.approx(0.1)
    assert r.json()["cost"]["total_100"] == 6.0
    r = client.post("/api/standard-parts/cost", json={"lines": [{"part_id": tube, "length_mm": 500, "count": 2}]})
    assert r.json()["lines"][0]["mode"] == "length" and r.json()["total_100"] == 24.0
    bad = {"lines": [{"part_id": tube, "length_mm": -1}]}
    assert client.post("/api/standard-parts/cost", json=bad).status_code == 422



# --- Renamed parts -----------------------------------------------------------

OLD_ID = "visaton-frs-8-8-2004--visaton-price-list-csv-13-oct-2026"
NEW_ID = "visaton-frs-8-8-2004--sos-electronic-eu"


def test_sos_electronic_rows():
    for pid in (NEW_ID, "visaton-frs-8-m-8-2001--sos-electronic-eu", "visaton-bg-20-8-3020--sos-electronic-eu"):
        part = PARTS[pid]
        assert part.supplier == "SOS Electronic, EU"
        assert part.links[0]["url"] == "https://www.soselectronic.com/en-gb/speakers"
        assert part.source_files == ["standard-parts/price-lists/visaton-2026-10-13.csv"]
        assert "import VAT" in part.note


def test_renamed_part_keeps_its_old_id():
    assert LIB.aliases[OLD_ID] == NEW_ID and LIB.current_id(OLD_ID) == NEW_ID
    assert PARTS[OLD_ID] is PARTS[NEW_ID]
    old = sp.cost_lines([{"part_id": OLD_ID, "quantity": 2}], PARTS, None, 0.2, 0.33)
    new = sp.cost_lines([{"part_id": NEW_ID, "quantity": 2}], PARTS, None, 0.2, 0.33)
    assert old["total_100"] == new["total_100"] and not old["unknown"]
    # Each part is listed once, under its current id.
    listed = [p.id for s in LIB.sections for sub in s.subsections for p in sub.parts]
    assert OLD_ID not in listed and NEW_ID in listed


def test_renamed_parts_block_is_validated():
    table = "## 1. A\n\n### 1.1 B\n\n| a | b | c | d | e | f | g | h |\n|---|---|---|---|---|---|---|---|\n" \
            "| Tube | Brass | 1 m | S, UK — [l](https://x.uk) | £10 | — | 1 | — |\n"
    ok = sp.parse_library(table + "\n<!-- renamed-parts\ntube--old: tube--s-uk\n-->\n")
    assert ok.parts["tube--old"].id == "tube--s-uk"
    for bad in ("tube--old: nope--s-uk", "tube--s-uk: tube--s-uk"):
        with pytest.raises(sp.LibraryError):
            sp.parse_library(table + f"\n<!-- renamed-parts\n{bad}\n-->\n")


def test_saving_a_concept_with_an_old_id_stores_the_current_one(client):
    r = client.post("/api/concepts", json={"name": "Old id", "lines": [{"part_id": OLD_ID, "quantity": 1}]})
    assert r.status_code == 201, r.text
    assert r.json()["lines"][0]["part_id"] == NEW_ID
    assert client.get("/api/standard-parts").json()["aliases"][OLD_ID] == NEW_ID


# --- 3D shapes ---------------------------------------------------------------


def test_part_shapes_parse_with_one_entry_per_variant():
    shaped = {pid: p for pid, p in PARTS.items() if p.shapes}
    assert len(shaped) >= 70
    cyl = PARTS["internally-frosted-cylinder-shade--j-moncrieff-uk"].shapes[0]
    assert cyl == {"shape": "tube", "od": 80, "id": 74, "length": 210, "look": "glass_frosted", "assumed": "wall 3 mm"}
    sheet = PARTS["brass-sheet-sample-small-sheet--the-metal-store-uk"]
    assert [s["width"] for s in sheet.shapes] == [45, 250]
    for p in shaped.values():
        assert len(p.shapes) == max(len(p.options), 1), p.id
    # Parts without stated sizes have no shape: the view draws a labelled placeholder.
    assert PARTS["brass-inline-lamp-kit-oaklk1--oaklea-woodcraft-uk"].shapes == []


def test_shape_block_is_validated():
    table = "## 1. A\n\n### 1.1 B\n\n| a | b | c | d | e | f | g | h |\n|---|---|---|---|---|---|---|---|\n" \
            "| Tube | Brass | 1 m | S, UK — [l](https://x.uk) | £10 | — | 1 | — |\n"
    ok = sp.parse_library(table + '\n<!-- part-shapes\ntube--s-uk: {shape: rod, d: 10, length: 50, assumed: "x"}\n-->\n')
    assert ok.parts["tube--s-uk"].shapes == [{"shape": "rod", "d": 10, "length": 50, "assumed": "x"}]
    for bad in ("nope--s-uk: {shape: rod, d: 10, length: 50}", "tube--s-uk: {shape: blob, d: 10}",
                "tube--s-uk: {shape: rod, d: 10}", "tube--s-uk: {shape: rod, d: 10, length: 50, width: 3}",
                "tube--s-uk: {shape: tube, od: 10, id: 12, length: 5}", "tube--s-uk: {shape: rod, d: 0, length: 5}",
                "tube--s-uk: {shape: rod, d: 10, length: 50, look: gold}",
                "tube--s-uk: [{shape: rod, d: 1, length: 2}, {shape: rod, d: 1, length: 2}]"):
        with pytest.raises(sp.LibraryError):
            sp.parse_library(table + f"\n<!-- part-shapes\n{bad}\n-->\n")


def test_material_looks():
    look = lambda pid: sp.look_for(PARTS[pid])  # noqa: E731
    assert look("es-e27-shade-ring-s-lilley-spare--lampspares-uk") == "brass"
    assert look("cz108-round-tube-polished--the-metal-store-uk") == "brass"
    assert look("small-clear-glass-dome-30-mm-fitter--j-moncrieff-uk") == "glass"
    assert look("150-mm-opal-globe-80-mm-fitter-neck--j-moncrieff-uk") == "glass_opal"
    assert look("internally-frosted-dome-12-mm-fitter--j-moncrieff-uk") == "glass_frosted"
    assert look("clear-extruded-tube-60-5-mm-1-m--the-clear-plastic-shop-uk") == "acrylic"
    assert look("premium-beech-plywood-18-mm-glue-class-3--cts-diy-uk") == "wood"
    assert look("perforated-aluminium-r3-t6-1-5-mm--f-h-brundle-uk") == "aluminium"
    assert look("postal-tubes-with-end-caps-raja--morplan-uk") == "paper"
    assert look("visaton-grille-10-rs-round--farnell-uk") == "black"
    assert look("visaton-frs-8-8-2004--sos-electronic-eu") == "electronics"
    # "cone" alone isn't a driver: the metal spinners' cones are metal.
    assert look("cones-domes-hemispheres--winward-engineering-aldridge-uk") == "brass"
    assert sp.look_for(PARTS["numbered-knob--hificollective-uk"], 1) == "black"


def test_most_concept_parts_have_shapes():
    used = {ln["part_id"] for c in CONCEPTS for ln in c.lines}
    shaped = {pid for pid in used if PARTS[pid].shapes}
    # Electronics modules and the lamp kit have no stated sizes; everything else is drawn.
    assert used - shaped <= {
        "brass-inline-lamp-kit-oaklk1--oaklea-woodcraft-uk",
        "adafruit-universal-usb-dc-solar-charger-bq24074-ada4755--the-pi-hut-uk",
        "wondom-jab3-2-50-w-bt-5-0-adau1701-dsp--ebay-uk",
        "solid-metal-control-knobs--knobzone-uk",
    }, used - shaped


def test_concept_api_keeps_the_3d_view(client):
    view = {"dx": 40, "dy": -5, "dz": 0, "rx": 0, "ry": 30, "rz": 0, "repeat": 3, "stack": False, "form": "auto"}
    body = {"name": "Feet", "lines": [{"part_id": "bun-feet--cousins-uk", "quantity": 3, "view": view}]}
    r = client.post("/api/concepts", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["lines"][0]["view"] == view
    assert r.json()["cost"]["total_100"] == 10.5  # the view never changes the cost
    cid = r.json()["id"]
    assert client.get(f"/api/concepts/{cid}").json()["lines"][0]["view"]["repeat"] == 3
    for bad in ({"repeat": 0}, {"repeat": 65}, {"dx": 1e6}, {"form": "cube"}):
        b = {"name": "x", "lines": [{"part_id": "bun-feet--cousins-uk", "quantity": 1, "view": bad}]}
        assert client.post("/api/concepts", json=b).status_code == 422
    # Lines without a view are saved without one.
    r = client.post("/api/concepts", json={"name": "y", "lines": [{"part_id": "bun-feet--cousins-uk", "quantity": 1}]})
    assert "view" not in r.json()["lines"][0]


def test_library_api_sends_shapes_and_looks(client):
    parts = [p for s in client.get("/api/standard-parts").json()["sections"] for sub in s["subsections"] for p in sub["parts"]]
    ring = next(p for p in parts if p["id"] == "es-e27-shade-ring-s-lilley-spare--lampspares-uk")
    assert ring["look"] == "brass" and ring["shapes"][0]["shape"] == "ring"


def test_seed_concept_views_are_valid_placements():
    """Every concept's starting arrangement in the 3D view is one the builder could save."""
    from app.api.standard_parts import LineView

    placed = 0
    for concept in sp.load_concepts():
        for line in concept.lines:
            if "view" in line:
                assert set(line["view"]) <= set(LineView.model_fields), (concept.name, line)
                LineView.model_validate(line["view"])
                placed += 1
        assert any("view" in line for line in concept.lines), f"{concept.name} has no arrangement"
    assert placed >= 15

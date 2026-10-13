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
    for p in PARTS.values():
        assert p.supplier and p.links, p.id
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
    assert tambour["name"] == "Tambour" and tambour["cost"]["total_100"] == 63.45


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

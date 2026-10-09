"""Product registry: every product has a template and a complete generator, and services don't name products."""

import re
from pathlib import Path

import pytest

from app.cad.generator import REQUIRED
from app.products import get_product, products
from app.services.templates import load_template

APP = Path(__file__).resolve().parents[1] / "app"


def test_faro_is_registered():
    p = get_product("faro")
    assert p is not None and p.label == "Faro" and p.noun == "lamp"
    assert get_product(None) is None and get_product("nope") is None


@pytest.mark.parametrize("key", list(products()))
def test_generator_implements_the_interface(key):
    gen = products()[key].generator
    missing = [name for name in REQUIRED if not hasattr(gen, name)]
    assert missing == [], f"{key} generator lacks {missing}"


@pytest.mark.parametrize("key", list(products()))
def test_template_matches_generator(key):
    """Every template part with a cad_key names a body the generator builds; the defaults validate."""
    product, tpl = products()[key], load_template(key)
    gen = product.generator
    keys = [p["cad_key"] for p in tpl["parts"] if p.get("cad_key")]
    assert set(keys) <= set(gen.PART_KEYS)
    assert gen.validate(dict(tpl["cad_parameters"])).ok
    assert set(product.wall_params) <= set(gen.PART_KEYS)
    assert set(product.wall_limit_parts) <= set(gen.PART_KEYS)
    assert {v for v in product.wall_params.values()} <= {d.key for d in gen.PARAMS}
    assert set(gen.UNSCALED_PARAMS) <= {d.key for d in gen.PARAMS}


def test_services_do_not_name_a_product():
    """Product-specific behaviour goes through app.products, not `template == "faro"` checks in the services."""
    offenders = []
    for path in (APP / "services").glob("*.py"):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"template\s*[!=]=\s*[\"']", line):
                offenders.append(f"{path.name}:{n}: {line.strip()}")
    assert offenders == []


def test_templates_endpoint(client):
    r = client.get("/api/templates")
    assert r.status_code == 200
    assert {"key": "faro", "label": "Faro", "summary": "lighthouse lamp", "noun": "lamp"} in r.json()


def test_unknown_template_rejected(client):
    r = client.post("/api/projects", json={"name": "X", "template": "toaster"})
    assert r.status_code == 422
    assert "Unknown product template" in r.text


def test_blank_project_has_no_product(client):
    r = client.post("/api/projects", json={"name": "Blank"})
    assert r.status_code == 201 and r.json()["template"] is None
    assert client.get(f"/api/projects/{r.json()['id']}/cad").status_code == 404


def test_project_carries_its_product_wording(client):
    """The front end words every page from `project.product` (noun, label, runtime basis), never from a literal."""
    faro = client.post("/api/projects", json={"name": "F", "template": "faro"}).json()
    atelier = client.post("/api/projects", json={"name": "A", "template": "atelier"}).json()
    assert faro["product"]["noun"] == "lamp" and faro["product"]["label"] == "Faro"
    assert faro["product"]["runtime_basis"] == "at full brightness with every light on"
    assert atelier["product"] == {**atelier["product"], "key": "atelier", "label": "Atelier", "noun": "speaker"}
    assert "volume" in atelier["product"]["runtime_basis"]
    assert {p["id"]: p["product"]["noun"] for p in client.get("/api/projects").json()}[atelier["id"]] == "speaker"
    # Only a template with a premium edition shows its price and targets on the Cost-down page
    assert client.get(f"/api/projects/{faro['id']}/pricing").json()["premium_edition"] is True
    assert client.get(f"/api/projects/{atelier['id']}/pricing").json()["premium_edition"] is False

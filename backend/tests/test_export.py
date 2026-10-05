import io
import json
import struct
import zipfile

import cadquery as cq
import pytest

from app.cad import export, faro
from app.config import settings
from app.services.templates import load_template

DEFAULTS = load_template("faro")["cad_parameters"]


@pytest.fixture(scope="module")
def parts():
    return faro.build(DEFAULTS)


def test_one_valid_solid_per_part(parts):
    assert list(parts) == faro.PART_KEYS
    info = export.part_info(parts)
    for key, i in info.items():
        assert i["valid"], key
        assert i["volume_mm3"] > 0, key


def test_overall_height_matches_parameter(parts):
    info = export.part_info(parts)
    top = max(i["z_range_mm"][1] for i in info.values())
    bottom = min(i["z_range_mm"][0] for i in info.values())
    assert top - bottom == pytest.approx(DEFAULTS["overall_height"], abs=0.01)


def test_height_change_changes_geometry():
    tall = faro.build({**DEFAULTS, "overall_height": 520})
    info = export.part_info(tall)
    assert info["top_cap"]["z_range_mm"][1] == pytest.approx(520, abs=0.01)
    assert info["main_body"]["size_mm"][2] == pytest.approx(368, abs=0.01)


def test_part_export_step_and_stl(parts, tmp_path):
    files = export.export_part(parts["main_body"], tmp_path, "main_body")
    step = next(f.path for f in files if f.format == "step")
    stl = next(f.path for f in files if f.format == "stl")
    assert step.read_text().startswith("ISO-10303-21;")
    reimported = cq.importers.importStep(str(step))
    assert len(reimported.solids().vals()) == 1
    assert reimported.val().Volume() == pytest.approx(parts["main_body"].val().Volume(), rel=1e-3)
    data = stl.read_bytes()
    n_triangles = struct.unpack("<I", data[80:84])[0]
    assert n_triangles > 100 and len(data) == 84 + 50 * n_triangles


def test_assembly_export(parts, tmp_path):
    files = export.export_assembly(faro.assembly(parts), parts, tmp_path, "faro")
    by_fmt = {f.format: f.path for f in files}
    assert set(by_fmt) == {"step", "stl", "glb"}

    step = by_fmt["step"]
    reimported = cq.importers.importStep(str(step))
    assert len(reimported.solids().vals()) == len(faro.PART_KEYS)
    text = step.read_text()
    for key in faro.PART_KEYS:
        assert f"PRODUCT('{key}'" in text

    glb = by_fmt["glb"].read_bytes()
    assert glb[:4] == b"glTF"
    json_len = struct.unpack("<I", glb[12:16])[0]
    doc = json.loads(glb[20 : 20 + json_len])
    assert set(faro.PART_KEYS) <= {n.get("name") for n in doc["nodes"]}


def test_generate_endpoint_creates_versions_and_downloads(client, faro_project):
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    r1 = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params})
    assert r1.status_code == 201, r1.text
    r2 = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": {**params, "overall_height": 480}})
    m1, m2 = r1.json(), r2.json()
    assert (m1["version"], m2["version"]) == (1, 2)
    assert m2["part_info"]["top_cap"]["z_range_mm"][1] == pytest.approx(480, abs=0.5)

    # Per-part STEP + STL for every part, plus assembly STEP/STL/GLB.
    outs = {(o["part_key"], o["format"]) for o in m2["outputs"]}
    for key in faro.PART_KEYS:
        assert (key, "step") in outs and (key, "stl") in outs
    assert {(None, "step"), (None, "stl"), (None, "glb")} <= outs

    # v1 files are untouched by v2 (immutable versions).
    v1_step = next(o["path"] for o in m1["outputs"] if o["part_key"] is None and o["format"] == "step")
    assert (settings.data_dir / v1_step).exists()
    assert client.get(f"/files/{v1_step}").content.startswith(b"ISO-10303-21;")

    state = client.get(f"/api/projects/{pid}/cad").json()
    assert state["parameters"]["overall_height"] == 480
    assert state["latest"]["version"] == 2

    z = client.get(f"/api/projects/{pid}/cad/models/2/download.zip")
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "faro_assembly.step" in names and "parts/base.step" in names


def test_repeated_regeneration_in_one_session_is_stable(client, faro_project):
    """Many regenerations + exports in one process must keep producing valid, distinct versions."""
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    for i in range(15):
        p = {**params, "overall_height": 380 + i * 10, "wall_thickness": 1.5 + (i % 3) * 0.5}
        r = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": p})
        assert r.status_code == 201, (i, r.text)
        model = r.json()
        assert model["version"] == i + 1
        assert all(info["valid"] for info in model["part_info"].values())
        assert model["part_info"]["top_cap"]["z_range_mm"][1] == pytest.approx(p["overall_height"], abs=0.5)
        for out in model["outputs"]:
            assert (settings.data_dir / out["path"]).stat().st_size > 0
    assert client.get("/api/health").status_code == 200

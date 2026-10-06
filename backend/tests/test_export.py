import io
import json
import struct
import zipfile

import pytest
from build123d import Cylinder, Pos, import_step

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
    assert top == pytest.approx(DEFAULTS["overall_height"], abs=0.01)  # finial ball top
    assert info["finial"]["z_range_mm"][1] == pytest.approx(DEFAULTS["overall_height"], abs=0.01)
    assert bottom == pytest.approx(-(faro.FELT_T + faro.FELT_BACKING), abs=0.01)  # felt pad below the base


def test_prototype_proportions(parts):
    """The default Faro is the approved prototype at 300 mm (faro/params.py on the prototype branch)."""
    info = export.part_info(parts)
    assert info["base"]["size_mm"][0] == pytest.approx(113, abs=0.1)
    assert info["base"]["z_range_mm"] == pytest.approx([0, 27], abs=0.01)
    assert info["band_cream"]["size_mm"][0] == pytest.approx(97, abs=0.1)
    assert info["tower"]["z_range_mm"] == pytest.approx([33, 197], abs=0.01)
    assert info["tower"]["size_mm"][0] == pytest.approx(92, abs=0.2)
    assert info["gallery"]["size_mm"][0] == pytest.approx(90, abs=0.1)
    assert info["lantern_frame"]["z_range_mm"] == pytest.approx([206.7, 248], abs=0.01)
    assert info["cap"]["size_mm"][0] == pytest.approx(71, abs=0.1)
    d = faro.derived({k: float(v) for k, v in DEFAULTS.items()})
    assert d["cap_top_z"] == pytest.approx(281, abs=0.01)
    assert [a for _, a in d["windows"]] == [0, 90, 180, 270, 0]  # spiral: first and last on the front


def test_spun_shells_have_the_wall_thickness(parts):
    """Base, tower and cap are thin spun shells, not solid printed parts."""
    w = DEFAULTS["wall_thickness"]
    for key in ("tower", "cap", "base"):
        sec = faro.model(DEFAULTS).sections[key]
        perimeter = sum(e.length for e in sec.outer_wire().edges())
        assert sec.area / (perimeter / 2) == pytest.approx(w, rel=0.25), key  # area ≈ wall × centreline length


def test_bayonet_fits(parts):
    info = faro.model(DEFAULTS).info
    assert info["bayonet"]["locked_clash_mm3"] == 0
    assert info["bayonet"]["entry_clash_mm3"] == 0
    assert info["bayonet"]["lug_under_lip_mm"] > 1
    assert info["bayonet"]["led_lifts_out"]
    assert info["glass_frame_clash_mm3"] == 0


def test_no_clashes_between_neighbours(parts):
    pairs = [("base", "band_cream"), ("band_cream", "tower"), ("tower", "gallery"), ("gallery", "lantern_glass"),
             ("lantern_glass", "lantern_frame"), ("tower", "diffuser"), ("tower", "knob"), ("tower", "dimmer"),
             ("weight_plate", "battery"), ("base", "weight_plate"), ("cap", "finial"), ("diffuser", "tower_light"),
             ("gallery", "railing"), ("cap", "cap_spigot")]
    for a, b in pairs:
        common = parts[a] & parts[b]
        vol = 0.0 if common is None else common.volume
        assert vol < 0.5, (a, b, vol)


def test_height_change_changes_geometry():
    tall = faro.build({**DEFAULTS, "overall_height": 400})
    info = export.part_info(tall)
    assert info["finial"]["z_range_mm"][1] == pytest.approx(400, abs=0.01)
    base_info = export.part_info(faro.build(DEFAULTS))
    assert info["tower"]["size_mm"][2] == pytest.approx(base_info["tower"]["size_mm"][2] + 100, abs=0.01)


def test_windows_cut_and_removed():
    plain = export.part_info(faro.build({**DEFAULTS, "window_count": 0}))
    windowed = export.part_info(faro.build(DEFAULTS))
    assert plain["tower"]["volume_mm3"] > windowed["tower"]["volume_mm3"] + 100  # five arched openings


def test_part_export_step_and_stl(parts, tmp_path):
    files = export.export_part(parts["tower"], tmp_path, "tower")
    step = next(f.path for f in files if f.format == "step")
    stl = next(f.path for f in files if f.format == "stl")
    assert step.read_text().startswith("ISO-10303-21;")
    reimported = import_step(str(step))
    assert len(reimported.solids()) == 1
    assert reimported.solids()[0].volume == pytest.approx(parts["tower"].volume, rel=1e-3)
    data = stl.read_bytes()
    n_triangles = struct.unpack("<I", data[80:84])[0]
    assert n_triangles > 100 and len(data) == 84 + 50 * n_triangles


def test_assembly_export(parts, tmp_path):
    files = export.export_assembly(faro.assembly(parts), parts, tmp_path, "faro", colours=faro.PART_COLOURS,
                                   two_tone=faro.preview_two_tone(DEFAULTS))
    by_fmt = {f.format: f.path for f in files}
    assert set(by_fmt) == {"step", "stl", "glb"}

    reimported = import_step(str(by_fmt["step"]))
    assert len(reimported.solids()) == len(faro.PART_KEYS)
    text = by_fmt["step"].read_text()
    for key in faro.PART_KEYS:
        assert f"'{key}'" in text

    glb = by_fmt["glb"].read_bytes()
    assert glb[:4] == b"glTF"
    json_len = struct.unpack("<I", glb[12:16])[0]
    doc = json.loads(glb[20 : 20 + json_len])
    names = {n.get("name") for n in doc["nodes"]}
    assert set(faro.PART_KEYS) <= names
    assert "tower_lower" in names  # red lower section split out for the preview only


def test_generate_endpoint_creates_versions_and_downloads(client, faro_project):
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    r1 = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": params})
    assert r1.status_code == 201, r1.text
    r2 = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": {**params, "overall_height": 320}})
    m1, m2 = r1.json(), r2.json()
    assert (m1["version"], m2["version"]) == (1, 2)
    assert m2["part_info"]["finial"]["z_range_mm"][1] == pytest.approx(320, abs=0.5)

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
    assert state["parameters"]["overall_height"] == 320
    assert state["latest"]["version"] == 2
    assert len(state["production_changes"]) >= 10

    z = client.get(f"/api/projects/{pid}/cad/models/2/download.zip")
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "faro_assembly.step" in names and "parts/base.step" in names


def test_repeated_regeneration_in_one_session_is_stable(client, faro_project):
    """Several regenerations + exports in one process must keep producing valid, distinct versions."""
    pid = faro_project["id"]
    params = client.get(f"/api/projects/{pid}/cad").json()["parameters"]
    for i in range(5):
        p = {**params, "overall_height": 290 + i * 10, "wall_thickness": 1.2 + (i % 3) * 0.3}
        r = client.post(f"/api/projects/{pid}/cad/generate", json={"parameters": p})
        assert r.status_code == 201, (i, r.text)
        model = r.json()
        assert model["version"] == i + 1
        assert all(info["valid"] for info in model["part_info"].values())
        assert model["part_info"]["finial"]["z_range_mm"][1] == pytest.approx(p["overall_height"], abs=0.5)
        for out in model["outputs"]:
            assert (settings.data_dir / out["path"]).stat().st_size > 0
    assert client.get("/api/health").status_code == 200


def test_diffuser_covers_only_the_window_zone(parts):
    """Option 3: the opal tube runs 5 mm past the lowest and highest window and stands on a spider."""
    p = {k: float(v) for k, v in DEFAULTS.items()}
    d = faro.derived(p)
    wins = faro.windows(p)
    lo = wins[0][0] - p["window_height"] / 2 - faro.DIFFUSER_OVERLAP
    hi = wins[-1][0] + p["window_height"] / 2 + faro.DIFFUSER_OVERLAP
    info = export.part_info(parts)
    assert info["diffuser"]["z_range_mm"] == pytest.approx([lo, hi], abs=0.01)
    assert d["diffuser_length"] < 0.6 * d["tower_height"]
    # The spider on the tower-light spine carries it: touching, not clashing.
    common = parts["diffuser"] & parts["tower_light"]
    assert (0.0 if common is None else common.volume) < 0.5
    spider_top = Pos(0, 0, lo - 0.5) * Cylinder(d["diffuser_od"] / 2 - 0.5, 0.2)
    assert (parts["tower_light"] & spider_top).volume > 1
    # With no windows the tube runs the full height again.
    plain = faro.derived({**p, "window_count": 0})
    assert plain["diffuser_length"] > d["diffuser_length"] + 50


def test_gallery_is_a_spun_shell_open_underneath(parts):
    """Option 2: 1 mm spun brass shell plus a locating ring, far lighter than the solid turned ring."""
    p = {k: float(v) for k, v in DEFAULTS.items()}
    d = faro.derived(p)
    g = parts["gallery"]
    zt, zg = d["tower_top_z"], d["gallery_top_z"]
    rg = p["gallery_diameter"] / 2
    solid_ring = 3.1416 * (rg**2 - d["gallery_bore_r"] ** 2) * p["gallery_height"]
    assert g.volume < 0.4 * solid_ring
    # Hollow between the locating ring and the skirt, just above the tower top.
    probe = Pos(0, 0, (zt + zg) / 2) * Cylinder(rg - 3, 1.0) - Pos(0, 0, (zt + zg) / 2) * Cylinder(d["r_out"](zt) + 1, 1.0)
    common = g & probe
    assert (0.0 if common is None else common.volume) < 0.5
    assert g.is_valid

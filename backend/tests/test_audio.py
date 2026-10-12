"""The speaker acoustic and power model (pure) and the runtime basis per product."""

import math

import pytest
import yaml

from app import audio, electrical
from app.config import SEED_DIR

TPL = yaml.safe_load((SEED_DIR / "products" / "atelier.yaml").read_text())
FARO = yaml.safe_load((SEED_DIR / "products" / "faro.yaml").read_text())


def test_closed_box_alignment_by_hand():
    out = audio.evaluate(TPL["audio"], 0.74)
    d = TPL["audio"]["driver"]
    alpha = d["vas_l"] / 0.74
    assert out["fc_hz"] == round(d["fs_hz"] * math.sqrt(1 + alpha))
    assert out["qtc"] == pytest.approx(d["qts"] * math.sqrt(1 + alpha), abs=0.01)
    smaller = audio.evaluate(TPL["audio"], 0.5)
    assert smaller["fc_hz"] > out["fc_hz"]
    assert out["alignment"] == "sealed" and "pr_moving_mass_g" not in out  # sealed box (user, Oct 2026)
    with_pr = {**TPL["audio"], "passive_radiator": TPL["audio"]["passive_radiator_option"]}
    a, b = audio.evaluate(with_pr, 0.74), audio.evaluate(with_pr, 0.5)
    assert a["alignment"] == "passive_radiator" and b["pr_moving_mass_g"] > a["pr_moving_mass_g"]


def test_sealed_box_bass_extension_with_dsp():
    """-3/-6 dB points of a second-order high-pass, and the DSP boost moving them down."""
    out = audio.evaluate(TPL["audio"], 0.75)
    assert audio._sealed_db(out["f3_hz"], out["fc_hz"], out["qtc"]) == pytest.approx(-3.0, abs=0.15)
    assert out["f6_hz"] < out["f3_hz"] < out["fc_hz"] * 1.1
    assert out["dsp_bass_boost_db"] == TPL["audio"]["dsp_bass_boost_db"] > 0
    assert out["f3_dsp_hz"] < out["f3_hz"] and out["f6_dsp_hz"] < out["f6_hz"]
    assert out["f6_dsp_hz"] <= TPL["audio"]["target_low_hz"]  # spec: 80 Hz (−6 dB) with the DSP bass enhancement


def test_excursion_spl_rises_12_db_per_octave_and_with_area():
    a = audio.excursion_spl(15, 2.5, 100)
    assert audio.excursion_spl(15, 2.5, 200) - a == pytest.approx(12.04, abs=0.05)
    assert audio.excursion_spl(30, 2.5, 100) - a == pytest.approx(6.02, abs=0.05)
    out = audio.evaluate(TPL["audio"], 0.74)
    full = out["full_spl_from_hz"]
    assert audio.excursion_spl(TPL["audio"]["driver"]["sd_cm2"], TPL["audio"]["driver"]["xmax_mm"], full) == \
        pytest.approx(TPL["audio"]["target_spl_db"], abs=0.1)


def test_spec_loudness_current_and_charge_time():
    out = audio.evaluate(TPL["audio"], 0.74, TPL["electrical"]["battery"])
    assert out["thermal_spl_db"] == pytest.approx(84 + 10 * math.log10(20), abs=0.1) and out["spl_ok"]
    assert out["peak_input_w"] == pytest.approx(20 / (0.85 * 0.9), abs=0.1)
    assert out["peak_cell_current_a"] == pytest.approx(out["peak_current_a"] / 2, abs=0.06) and out["current_ok"]
    # 2 x 3 Ah at 0.5 C x 4.2 V = 12.6 W < 20 W x 0.88: the cells limit charging
    assert out["charge_power_w"] == pytest.approx(12.6) and out["charge_ok"] and out["charge_h"] <= 3
    assert out["unverified"]  # placeholder Thiele-Small values


def test_runtime_basis_per_product():
    faro = electrical.estimate(FARO["electrical"], 8)
    assert faro["basis"] == electrical.DEFAULT_BASIS and faro["note"].startswith("Full brightness")
    at = electrical.estimate(TPL["electrical"], 15)
    assert at["basis"] == "at 50% volume (average music)" and "50% volume" in at["note"]
    assert at["hours"] >= 15 and at["status"] == "pass"


def test_faro_has_no_acoustic_model(client, faro_project):
    r = client.get(f"/api/projects/{faro_project['id']}/audio")
    assert r.status_code == 200 and r.json()["applicable"] is False

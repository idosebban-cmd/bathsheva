import { useEffect, useState } from "react";
import { api, errorText, type Audio } from "../api";
import { UnverifiedBadge } from "./Badges";
import { useProject } from "./useProject";

function Check({ ok }: { ok: boolean | undefined }) {
  return ok ? <span>✓</span> : <span className="warning-text">✗</span>;
}

/** Speaker acoustics and power: box tuning, loudness, bass excursion, battery current and charge time. */
export default function AudioCard() {
  const { project } = useProject();
  const [a, setA] = useState<Audio | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Audio>(`/api/projects/${project.id}/audio`).then(setA).catch((e) => setError(errorText(e)));
  }, [project]);

  if (error) return <p className="error">{error}</p>;
  if (!a || !a.applicable) return null;
  return (
    <section className="card">
      <h2>Sound and power {a.unverified && <UnverifiedBadge />}</h2>
      {a.alignment === "passive_radiator" ? (
        <p>
          The {a.box_l?.toFixed(2)} L air space behind the driver gives a closed-box resonance of {a.fc_hz} Hz (Qtc {a.qtc}); the
          rear passive radiator tuned to {a.pr_target_fb_hz} Hz extends the bass below that. Loudest clean level about{" "}
          <b>{a.thermal_spl_db} dB</b> at 1 m (target {a.target_spl_db} dB) <Check ok={a.spl_ok} />.
        </p>
      ) : (
        <p>
          A sealed box of {a.box_l?.toFixed(2)} L: resonance {a.fc_hz} Hz (Qtc {a.qtc}), −3 dB at about {a.f3_hz} Hz and −6 dB at
          about {a.f6_hz} Hz from the box alone. The DSP bass enhancement (up to +{a.dsp_bass_boost_db} dB) extends that to about{" "}
          <b>{a.f3_dsp_hz} Hz (−3 dB)</b> and {a.f6_dsp_hz} Hz (−6 dB) at normal listening levels. Loudest clean level about{" "}
          <b>{a.thermal_spl_db} dB</b> at 1 m (target {a.target_spl_db} dB) <Check ok={a.spl_ok} />. Full level from about{" "}
          {a.full_spl_from_hz} Hz up; below that the DSP's excursion limiter holds the bass back.
        </p>
      )}
      <table className="small">
        <thead>
          <tr><th>Check</th><th>Estimate</th><th>Limit or target</th><th /></tr>
        </thead>
        <tbody>
          <tr>
            <td>Loudness (thermal)</td><td>{a.thermal_spl_db} dB</td><td>≥ {a.target_spl_db} dB</td><td><Check ok={a.spl_ok} /></td>
          </tr>
          <tr>
            <td>Driver rated for the amplifier</td><td colSpan={2}>{a.driver}</td><td><Check ok={a.driver_power_ok} /></td>
          </tr>
          {a.peak_cell_current_a != null && (
            <tr>
              <td>Peak battery current</td><td>{a.peak_current_a} A ({a.peak_cell_current_a} A per cell)</td>
              <td>≤ {a.cell_max_a} A per cell</td><td><Check ok={a.current_ok} /></td>
            </tr>
          )}
          {a.charge_h != null && (
            <tr>
              <td>Charge time (USB-C PD)</td><td>{a.charge_h} h at {a.charge_power_w} W</td>
              <td>≤ {a.charge_target_h} h</td><td><Check ok={a.charge_ok} /></td>
            </tr>
          )}
          {a.alignment === "passive_radiator" && (
            <tr>
              <td>Radiator moving mass for {a.pr_target_fb_hz} Hz</td><td>{a.pr_moving_mass_g} g</td><td colSpan={2}>{a.radiator}</td>
            </tr>
          )}
        </tbody>
      </table>
      <h3>Bass at full excursion (dB at 1 m)</h3>
      <table className="small">
        <thead>
          <tr><th>Frequency</th>{a.bass?.map((b) => <th key={b.f_hz}>{b.f_hz} Hz</th>)}</tr>
        </thead>
        <tbody>
          <tr><td>Driver</td>{a.bass?.map((b) => <td key={b.f_hz}>{b.driver_db}</td>)}</tr>
          {a.alignment === "passive_radiator" && (
            <tr><td>Radiator</td>{a.bass?.map((b) => <td key={b.f_hz}>{b.radiator_db ?? "–"}</td>)}</tr>
          )}
        </tbody>
      </table>
      <p className="small muted">
        Sealed-box and excursion estimates from the template's driver and amplifier data (supplier to confirm the
        Thiele-Small parameters). The air volume comes from the CAD model, so it updates when the body changes.
      </p>
    </section>
  );
}

import { useEffect, useState } from "react";
import { api, errorText, type Runtime } from "../api";
import { UnverifiedBadge } from "./Badges";
import { useProject } from "./useProject";

const STATUS_TEXT: Record<string, string> = { pass: "meets the target", close: "just short of the target", fail: "below the target" };

/** Estimated battery runtime from the LED loads, against the runtime requirement, plus battery compliance flags. */
export default function RuntimeCard() {
  const { project } = useProject();
  const [rt, setRt] = useState<Runtime | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Runtime>(`/api/projects/${project.id}/runtime`).then(setRt).catch((e) => setError(errorText(e)));
  }, [project]);

  if (error) return <p className="error">{error}</p>;
  if (!rt || !rt.applicable) return null;
  const cls = rt.status === "pass" ? "" : "warning-text";
  return (
    <section className="card">
      <h2>Battery runtime {rt.unverified && <UnverifiedBadge />}</h2>
      <p className={cls}>
        Estimated <b>{rt.hours?.toFixed(1)} h</b> at full brightness with every light on
        {rt.target_h ? ` vs target ${rt.target_h} h: ${STATUS_TEXT[rt.status ?? ""] ?? ""}` : " (set a runtime target above)"}.
        {rt.without_tower_light_h ? ` Lantern only: ${rt.without_tower_light_h.toFixed(1)} h.` : ""}
      </p>
      <table className="small">
        <thead>
          <tr><th>Load</th><th>Full brightness</th><th>Runtime on its own</th><th>Source</th></tr>
        </thead>
        <tbody>
          {rt.loads?.map((l) => (
            <tr key={l.name}>
              <td>{l.name}</td>
              <td>{l.watts} W</td>
              <td>{l.hours_alone?.toFixed(1)} h</td>
              <td>{l.source} {!l.verified && <UnverifiedBadge />}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="small muted">
        Battery {rt.assumptions?.cells} × {rt.assumptions?.cell_capacity_mah} mAh at {rt.assumptions?.cell_voltage} V ={" "}
        {rt.battery_wh} Wh; {Number(rt.assumptions?.usable_fraction) * 100}% usable and a {Number(rt.assumptions?.driver_efficiency) * 100}%
        efficient driver deliver {rt.delivered_wh} Wh to {rt.load_w} W of LEDs. {rt.note}
      </p>
      {rt.compliance && rt.compliance.length > 0 && (
        <>
          <h3>Battery compliance (verify with a qualified person)</h3>
          <ul className="small">
            {rt.compliance.map((c) => <li key={c}>{c}</li>)}
          </ul>
        </>
      )}
    </section>
  );
}

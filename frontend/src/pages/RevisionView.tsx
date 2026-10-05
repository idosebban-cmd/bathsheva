import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorText, fileUrl, type CadState, type Revision } from "../api";
import { AssumptionBadge, ConfidenceBadge, SafetyBadge, UnverifiedBadge } from "../components/Badges";
import CadDownloads from "../components/CadDownloads";
import ModelViewer from "../components/ModelViewer";
import { useProject } from "../components/useProject";

const fmtMoney = (m: { amount: number | null; currency: string }) => (m.amount === null ? "TBD" : `${m.currency} ${m.amount}`);

export default function RevisionView() {
  const { project } = useProject();
  const { number } = useParams();
  const [rev, setRev] = useState<Revision | null>(null);
  const [current, setCurrent] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Revision>(`/api/projects/${project.id}/revisions/${number}`).then(setRev, (e) => setError(errorText(e)));
    if (project.template) api.get<CadState>(`/api/projects/${project.id}/cad`).then((s) => setCurrent(s.parameters), () => undefined);
  }, [project.id, project.template, number]);

  if (error) return <p className="error">{error}</p>;
  if (!rev) return <p>Loading…</p>;
  const s = rev.snapshot;
  const req = s.requirements;
  const glb = s.cad_model?.outputs.find((o) => o.part_key === null && o.format === "glb");
  const assumed = (f: string) => s.assumed_fields.includes(f) && <AssumptionBadge />;
  const decisionsByPart = new Map(s.decisions.filter((d) => d.part_id !== null).map((d) => [d.part_id, d]));

  return (
    <div className="stack">
      <section className="card revision-banner">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2>
            Revision {rev.number}: {rev.note || "(no note)"}
          </h2>
          <Link to=".." relative="path">← All revisions</Link>
        </div>
        <p className="small muted">
          Saved {new Date(rev.created_at).toLocaleString()} · read-only snapshot{s.cad_model ? ` · CAD v${s.cad_model.version}` : " · no CAD"}
        </p>
      </section>

      <div className="split">
        <section className="card">
          <h2>Requirements</h2>
          <dl className="tech">
            <div>
              <dt>Name</dt>
              <dd>{s.project.name}</dd>
            </div>
            <div>
              <dt>Dimensions {assumed("approx_dimensions")}</dt>
              <dd>
                {[req.approx_dimensions.height_mm, req.approx_dimensions.width_mm, req.approx_dimensions.depth_mm].map((v) => v ?? "TBD").join(" × ")} mm
              </dd>
            </div>
            <div>
              <dt>Retail price {assumed("target_retail_price")}</dt>
              <dd>{fmtMoney(req.target_retail_price)}</dd>
            </div>
            <div>
              <dt>Volume {assumed("production_volume")}</dt>
              <dd>{req.production_volume ?? "TBD"}</dd>
            </div>
            <div>
              <dt>Target unit cost {assumed("target_unit_cost")}</dt>
              <dd>{fmtMoney(req.target_unit_cost)}</dd>
            </div>
            <div>
              <dt>Markets {assumed("intended_markets")}</dt>
              <dd>{req.intended_markets.join(", ")}</dd>
            </div>
            <div>
              <dt>Power</dt>
              <dd>{req.power_type}</dd>
            </div>
          </dl>
        </section>
        {s.cad_parameters && (
          <section className="card">
            <h2>CAD parameters</h2>
            <table>
              <thead>
                <tr>
                  <th>Parameter</th>
                  <th>Rev {rev.number}</th>
                  <th>Current</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(s.cad_parameters).map(([k, v]) => {
                  const cur = current?.[k];
                  const changed = cur !== undefined && cur !== v;
                  return (
                    <tr key={k} className={changed ? "changed" : ""}>
                      <td>{k.replace(/_/g, " ")}</td>
                      <td>{v}</td>
                      <td>{cur ?? ""}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        )}
      </div>

      {s.cad_model && (
        <section className="card">
          <h2>CAD v{s.cad_model.version} (as saved)</h2>
          {glb && <ModelViewer url={fileUrl(glb.path)} />}
          <CadDownloads model={s.cad_model} projectId={project.id} />
        </section>
      )}

      <section className="card">
        <h2>Parts and recommendations</h2>
        <table>
          <thead>
            <tr>
              <th>Part</th>
              <th>Material / process (set)</th>
              <th>Recommendation at the time</th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody>
            {s.parts.map((p) => {
              const rec = s.recommendations.find((r) => r.part_id === p.id);
              const d = decisionsByPart.get(p.id);
              return (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>
                    {p.material || "—"} / {p.process || "—"}
                  </td>
                  <td>
                    {rec?.recommendation ? `${rec.recommendation.process_name} · ${rec.recommendation.material_name}` : "—"}
                    <div>
                      {rec && <ConfidenceBadge level={rec.confidence} />} {rec?.uses_unverified_data && <UnverifiedBadge />}{" "}
                      {rec && rec.safety_flags.length > 0 && <SafetyBadge />}
                    </div>
                  </td>
                  <td>{d ? <span className={`badge badge-status-${d.status}`}>{d.status}</span> : <span className="muted">—</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}

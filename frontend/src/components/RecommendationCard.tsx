import { useState } from "react";
import { api, errorText, type Explanation, type Recommendation } from "../api";
import { AssumptionBadge, ConfidenceBadge, SafetyBadge, UnverifiedBadge } from "./Badges";

const TECH_LABELS: Record<string, string> = {
  economic_volume: "Economic volume",
  tooling_cost: "Tooling cost",
  unit_cost: "Unit cost (relative)",
  as_made_finish: "As-made surface",
  wall_thickness: "Wall thickness",
  tolerances: "Tolerances",
  draft_angles: "Draft angles",
  bend_radius: "Bend radius",
  fastening: "Fastening / joining",
  finishing: "Finishing",
};

interface Props {
  rec: Recommendation;
  projectId: number;
  llmEnabled: boolean;
  onChanged: () => Promise<void>;
}

export default function RecommendationCard({ rec, projectId, llmEnabled, onChanged }: Props) {
  const [editing, setEditing] = useState(false);
  const [material, setMaterial] = useState(rec.recommendation?.material_name ?? "");
  const [process, setProcess] = useState(rec.recommendation?.process_name ?? "");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [explaining, setExplaining] = useState(false);

  async function decide(status: "accepted" | "rejected" | "edited") {
    setError("");
    try {
      await api.post(`/api/projects/${projectId}/decisions`, {
        part_id: rec.part_id,
        topic: "material_process",
        status,
        recommendation: rec,
        chosen: status === "edited" ? { material, process } : {},
        note,
      });
      setEditing(false);
      await onChanged();
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function explain() {
    setExplaining(true);
    setError("");
    try {
      const r = await api.post<{ explanation: Explanation }>(`/api/projects/${projectId}/recommendations/${rec.part_id}/explain`);
      setExplanation(r.explanation);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setExplaining(false);
    }
  }

  const unverified = rec.sources.filter((s) => !s.verified);
  const d = rec.decision;

  return (
    <article className="card rec-card" id={`rec-${rec.part_id}`}>
      <header className="rec-head">
        <h3>{rec.part_name}</h3>
        <div className="row">
          <ConfidenceBadge level={rec.confidence} />
          {rec.uses_unverified_data && <UnverifiedBadge title={`${unverified.length} unverified rule entries used`} />}
          {rec.safety_flags.length > 0 && <SafetyBadge />}
          {d && <span className={`badge badge-status-${d.status}`}>{d.status}</span>}
        </div>
      </header>

      {rec.recommendation ? (
        <p className="rec-main">
          <strong>Recommendation:</strong> {rec.recommendation.process_name} · {rec.recommendation.material_name}
        </p>
      ) : (
        <p className="rec-main">No recommendation</p>
      )}
      <p>{rec.summary}</p>
      {d && d.status !== "rejected" && d.chosen?.process && (
        <p className="small notice">
          Your decision: {d.chosen.process} · {d.chosen.material}
          {d.note && ` (${d.note})`}
        </p>
      )}

      {rec.safety_flags.length > 0 && (
        <div className="safety-box">
          <strong>Safety: needs human or manufacturer verification</strong>
          <ul>
            {rec.safety_flags.map((f) => (
              <li key={f.key}>
                {f.message} <span className="muted small">Verify with: {f.verify_with}.</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rec-grid">
        <section>
          <h4>Reason</h4>
          <ul>
            {rec.reason.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </section>
        <section>
          <h4>
            Assumptions <AssumptionBadge title="Inputs the recommendation relies on" />
          </h4>
          <ul>
            {rec.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
            {rec.uses_unverified_data && <li>Rule data is model-generated and unverified.</li>}
          </ul>
        </section>
        <section>
          <h4>Confidence: {rec.confidence}</h4>
          <p className="small">{rec.confidence_reason}</p>
          {rec.volume_sensitivity && rec.volume_sensitivity.length > 0 && (
            <p className="small muted">
              By volume: {rec.volume_sensitivity.map((v) => `${v.volume.toLocaleString()} → ${v.process_name}`).join(" · ")}
            </p>
          )}
        </section>
        <section>
          <h4>Questions that need answering</h4>
          {rec.open_questions.length ? (
            <ul>
              {rec.open_questions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
          ) : (
            <p className="muted small">None.</p>
          )}
        </section>
      </div>

      <section>
        <h4>Alternative options</h4>
        {rec.alternatives.length ? (
          <table>
            <thead>
              <tr>
                <th>Option</th>
                <th>When to prefer</th>
                <th>Why not chosen</th>
                <th>Tooling</th>
              </tr>
            </thead>
            <tbody>
              {rec.alternatives.map((a) => (
                <tr key={a.process_key}>
                  <td>
                    {a.process_name}
                    <div className="muted small">{a.material_name}</div>
                  </td>
                  <td>{a.when_to_prefer}</td>
                  <td>{a.why_not_chosen.join(" ")}</td>
                  <td className="small">{a.tooling_cost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted small">No other suitable options in the rules data.</p>
        )}
      </section>

      <details>
        <summary>Technical detail, risks and data sources</summary>
        <dl className="tech">
          {Object.entries(rec.technical).map(([k, v]) => (
            <div key={k}>
              <dt>{TECH_LABELS[k] ?? k}</dt>
              <dd>{Array.isArray(v) ? v.map((x, i) => <div key={i}>{x}</div>) : v}</dd>
            </div>
          ))}
        </dl>
        {rec.risks.length > 0 && (
          <>
            <h4>Manufacturing risks</h4>
            <ul>
              {rec.risks.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </>
        )}
        {(rec.constraints ?? []).map((c) => (
          <div key={c.key} className="notice small">
            <strong>{c.name}.</strong> {c.requirement || c.message}
            {c.excluded_processes.length > 0 && <> Excludes: {c.excluded_processes.join(", ")}.</>}
            {c.violations.map((v) => (
              <div key={v} className="error">
                {v}
              </div>
            ))}
          </div>
        ))}
        {rec.excluded.length > 0 && (
          <>
            <h4>Ruled out</h4>
            <ul className="small">
              {rec.excluded.map((e) => (
                <li key={e.process_key}>
                  {e.constraint && <span className="badge badge-constraint">design constraint</span>} {e.process_name}: {e.reason}
                </li>
              ))}
            </ul>
          </>
        )}
        <h4>Data sources</h4>
        <table className="small">
          <thead>
            <tr>
              <th>Rule</th>
              <th>Source</th>
              <th>Confidence</th>
              <th>Verified</th>
            </tr>
          </thead>
          <tbody>
            {rec.sources.map((s) => (
              <tr key={`${s.kind}:${s.key}`}>
                <td>
                  {s.kind}: {s.key}
                </td>
                <td>{s.source}</td>
                <td>{s.confidence}</td>
                <td>{s.verified ? "yes" : <UnverifiedBadge />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>

      {explanation && (
        <div className="ai-box">
          <strong>AI explanation</strong> <span className="muted small">(explains the rules result; does not change it)</span>
          <p>{explanation.plain_summary}</p>
          {explanation.tradeoffs.length > 0 && (
            <>
              <h4>Trade-offs</h4>
              <ul>
                {explanation.tradeoffs.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </>
          )}
          {explanation.caveats.length > 0 && (
            <>
              <h4>Caveats</h4>
              <ul>
                {explanation.caveats.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {editing && (
        <div className="edit-box">
          <div className="row">
            <input placeholder="Material" value={material} onChange={(e) => setMaterial(e.target.value)} />
            <input placeholder="Process" value={process} onChange={(e) => setProcess(e.target.value)} />
          </div>
          <input placeholder="Note (why you changed it)" value={note} onChange={(e) => setNote(e.target.value)} style={{ width: "100%" }} />
        </div>
      )}
      <div className="row">
        {rec.recommendation && (
          <button className="primary" onClick={() => decide("accepted")}>
            Accept
          </button>
        )}
        {editing ? (
          <button onClick={() => decide("edited")}>Save edit</button>
        ) : (
          <button onClick={() => setEditing(true)}>Edit</button>
        )}
        <button className="danger" onClick={() => decide("rejected")}>
          Reject
        </button>
        {llmEnabled && (
          <button onClick={explain} disabled={explaining}>
            {explaining ? "Explaining…" : "Explain with AI"}
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
    </article>
  );
}

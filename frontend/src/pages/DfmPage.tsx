import { useEffect, useState } from "react";
import { api, errorText, type DfmReport } from "../api";
import { AssumptionBadge, ConfidenceBadge, SafetyBadge, UnverifiedBadge } from "../components/Badges";
import { useProject } from "../components/useProject";

const ORDER = { fail: 0, warning: 1, info: 2, pass: 3 } as const;

export default function DfmPage() {
  const { project } = useProject();
  const [report, setReport] = useState<DfmReport | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      setReport(await api.get<DfmReport>(`/api/projects/${project.id}/dfm`));
    } catch (e) {
      setError(errorText(e));
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  if (!report) return <p>{error || "Loading…"}</p>;
  const s = report.summary;
  const checks = [...report.checks].sort((a, b) => ORDER[a.level] - ORDER[b.level]);

  return (
    <div className="stack dfm">
      <section className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2>DFM report: {report.project}</h2>
          <div className="row">
            <button onClick={load}>Refresh</button>
            <a href={`/api/projects/${project.id}/dfm.md`} download>
              <button>Download Markdown</button>
            </a>
          </div>
        </div>
        <p className="small muted">
          Generated {new Date(report.generated_at).toLocaleString()} · {report.cad_version ? `CAD v${report.cad_version}` : "no CAD generated yet"}
        </p>
        <p className="notice small">{report.disclaimer}</p>
        <div className="summary-tiles">
          <div className="tile fail">
            <b>{s.fail}</b> fail
          </div>
          <div className="tile warning">
            <b>{s.warning}</b> warnings
          </div>
          <div className="tile info">
            <b>{s.info}</b> info
          </div>
          <div className="tile pass">
            <b>{s.pass}</b> pass
          </div>
          <div className="tile fail">
            <b>{s.safety_items}</b> safety items
          </div>
          <div className="tile">
            <b>{s.open_questions}</b> open questions
          </div>
        </div>
      </section>

      <section className="card">
        <h2>Checks</h2>
        <table>
          <thead>
            <tr>
              <th>Result</th>
              <th>Area</th>
              <th>Check</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((c, i) => (
              <tr key={i}>
                <td>
                  <span className={`level level-${c.level}`}>{c.level}</span>
                </td>
                <td>{c.area}</td>
                <td>{c.title}</td>
                <td>
                  {c.detail} {c.unverified && <UnverifiedBadge />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>
          Safety items <SafetyBadge />
        </h2>
        <p className="small muted">Each needs verification by a qualified person, manufacturer or test lab.</p>
        <ul>
          {report.safety.map((f, i) => (
            <li key={i}>
              <strong>{f.part}:</strong> {f.message} <span className="muted small">Verify with: {f.verify_with}.</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Parts</h2>
        <table>
          <thead>
            <tr>
              <th>Part</th>
              <th>Process / material</th>
              <th>Basis</th>
              <th>Manufacturing risks</th>
            </tr>
          </thead>
          <tbody>
            {report.parts.map((p) => (
              <tr key={p.part_id}>
                <td>
                  {p.name}
                  <div>{p.confidence && <ConfidenceBadge level={p.confidence} />}</div>
                </td>
                <td>
                  {p.process || "TBD"}
                  <div className="muted small">{p.material}</div>
                </td>
                <td>
                  {p.basis}
                  {p.decision && <div className="muted small">decision: {p.decision}</div>}
                  {p.basis === "recommended" && p.uses_unverified_data && <UnverifiedBadge />}
                </td>
                <td>
                  <ul className="small">
                    {p.risks.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="split">
        <section className="card">
          <h2>Open questions</h2>
          <ul>
            {report.open_questions.map((q, i) => (
              <li key={i}>
                <strong>{q.part}:</strong> {q.question}
              </li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2>
            Assumptions <AssumptionBadge />
          </h2>
          <ul>
            {report.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

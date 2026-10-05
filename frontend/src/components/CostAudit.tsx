import { useEffect, useState } from "react";
import { api, errorText } from "../api";
import { UnverifiedBadge } from "./Badges";
import { gbp } from "./CostCharts";

interface AuditRow {
  rank: number;
  key: string;
  label: string;
  group: string;
  unit: string;
  low: number;
  high: number;
  value: number;
  source: string;
  confidence: string;
  verified: boolean;
  seed_file: string;
  seed_entry: string;
  swing: number;
  swing_pct: number;
  how_to_verify: string;
}

interface Audit {
  quantity: number;
  unit_cost_mid: number;
  configuration: { label: string; changes: { letter: string; label: string; option_label: string }[]; region_name: string };
  rows: AuditRow[];
  unverified: number;
  notes: string[];
}

const fmt = (v: number) => v.toLocaleString("en-GB", { maximumFractionDigits: 3 });
function seedValue(r: AuditRow): string {
  const span = r.low === r.high ? fmt(r.low) : `${fmt(r.low)}–${fmt(r.high)}`;
  return r.unit.startsWith("£") ? `£${span}${r.unit.slice(1)}` : `${span} ${r.unit}`;
}

/** Every seed value behind the best configuration's unit cost, ranked by impact. */
export default function CostAudit({ projectId }: { projectId: number }) {
  const [audit, setAudit] = useState<Audit | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Audit>(`/api/projects/${projectId}/cost-audit`).then(setAudit, (e) => setError(errorText(e)));
  }, [projectId]);

  if (error) return <section className="card error">{error}</section>;
  if (!audit) return <section className="card">Loading cost assumptions audit…</section>;
  const rows = showAll ? audit.rows : audit.rows.slice(0, 15);
  const changes = audit.configuration.changes.map((c) => `${c.letter}${c.option_label ? `: ${c.option_label}` : ""}`).join(", ");

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>Cost assumptions audit</h2>
        <div className="row">
          <a href={`/api/projects/${projectId}/cost-audit.md`} download>
            <button>Download Markdown</button>
          </a>
          <a href={`/api/projects/${projectId}/cost-audit.csv`} download>
            <button>Download CSV</button>
          </a>
        </div>
      </div>
      <p className="small">
        Every seed value behind the unit cost of the <strong>{audit.configuration.label.toLowerCase()}</strong> ({changes || "no changes"};{" "}
        {audit.configuration.region_name}): {gbp(audit.unit_cost_mid)} at {audit.quantity} units. Ranked by how much each moves the unit
        cost when changed by ±25%. Verify from the top. {audit.unverified} of {audit.rows.length} values are unverified.
      </p>
      <div className="table-wrap">
        <table className="small audit-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Assumption</th>
              <th>Seed value</th>
              <th>Used</th>
              <th>Source</th>
              <th>Impact ±25%</th>
              <th>How to verify</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <td>{r.rank}</td>
                <td>
                  {r.label}
                  <div className="muted">
                    <code>{r.seed_file}</code> → <code>{r.seed_entry}</code>
                  </div>
                </td>
                <td className="nowrap-cell">{seedValue(r)}</td>
                <td className="nowrap-cell">{r.unit.startsWith("£") ? `£${fmt(r.value)}${r.unit.slice(1)}` : `${fmt(r.value)} ${r.unit}`}</td>
                <td>
                  {r.source}
                  <div className="muted">{r.confidence} confidence</div>
                  {!r.verified && <UnverifiedBadge />}
                </td>
                <td className="nowrap-cell">
                  ±{gbp(Math.abs(r.swing))}
                  <div className="muted">{Math.abs(r.swing_pct).toFixed(1)}%</div>
                </td>
                <td>{r.how_to_verify || <span className="muted">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="link" onClick={() => setShowAll(!showAll)}>
        {showAll ? "Show top 15 only" : `Show all ${audit.rows.length} values`}
      </button>
      <ul className="small muted">
        {audit.notes.map((n, i) => (
          <li key={i}>{n}</li>
        ))}
      </ul>
    </section>
  );
}

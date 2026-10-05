import { useCallback, useEffect, useState } from "react";
import { api, errorText, type Bom, type BomRow } from "../api";
import { AssumptionBadge, SafetyBadge, UnverifiedBadge } from "../components/Badges";
import { useProject } from "../components/useProject";

function Flag({ flag }: { flag: string }) {
  if (flag === "unverified rule data") return <UnverifiedBadge />;
  if (flag === "safety: verify") return <SafetyBadge />;
  if (flag === "assumption") return <AssumptionBadge />;
  return <span className="badge">{flag}</span>;
}

export default function BomPage() {
  const { project } = useProject();
  const [bom, setBom] = useState<Bom | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setBom(await api.get<Bom>(`/api/projects/${project.id}/bom`));
    } catch (e) {
      setError(errorText(e));
    }
  }, [project.id]);
  useEffect(() => {
    load();
  }, [load]);

  async function update(row: BomRow, field: "quantity" | "cost_low" | "cost_high" | "supplier_notes", raw: string) {
    if (row.part_id === null) return;
    let value: string | number | null = raw;
    if (field !== "supplier_notes") value = raw.trim() === "" ? null : Number(raw);
    if (field === "quantity" && (value === null || (value as number) < 1)) return;
    if ((row[field] ?? null) === value) return;
    try {
      await api.patch(`/api/projects/${project.id}/parts/${row.part_id}`, { [field]: value });
      await load();
    } catch (e) {
      setError(errorText(e));
    }
  }

  if (!bom) return <p>{error || "Loading…"}</p>;
  const money = (v: number) => `£${v.toFixed(2)}`;

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>Bill of materials {bom.cad_version && <span className="muted">· sizes from CAD v{bom.cad_version}</span>}</h2>
        <a href={`/api/projects/${project.id}/bom.csv`} download>
          <button className="primary">Export CSV</button>
        </a>
      </div>
      {error && <p className="error">{error}</p>}
      <ul className="small muted">
        {bom.notes.map((n, i) => (
          <li key={i}>{n}</li>
        ))}
      </ul>
      <div className="table-wrap">
        <table className="bom">
          <thead>
            <tr>
              <th>#</th>
              <th>Part</th>
              <th>Qty</th>
              <th>Material</th>
              <th>Process</th>
              <th>Finish</th>
              <th>Size (mm)</th>
              <th>Status</th>
              <th>Unit cost £ (low–high)</th>
              <th>Supplier notes</th>
              <th>Flags</th>
            </tr>
          </thead>
          <tbody>
            {bom.rows.map((r) => (
              <tr key={r.item} className={r.derived ? "derived" : ""}>
                <td>{r.item}</td>
                <td style={{ paddingLeft: `${0.5 + r.level * 1.25}rem` }}>{r.name}</td>
                <td>
                  {r.derived ? (
                    r.quantity
                  ) : (
                    <input className="cell" type="number" min={1} defaultValue={r.quantity} onBlur={(e) => update(r, "quantity", e.target.value)} />
                  )}
                </td>
                <td>{r.material || <span className="muted">TBD</span>}</td>
                <td>{r.process || <span className="muted">TBD</span>}</td>
                <td>{r.finish}</td>
                <td className="small">{r.size_mm}</td>
                <td>
                  <span className={`badge badge-status-${r.status === "decided" ? "accepted" : r.status === "recommended" ? "edited" : ""}`}>{r.status}</span>
                </td>
                <td>
                  {r.derived ? (
                    <span className="muted">TBD</span>
                  ) : (
                    <span className="row nowrap">
                      <input className="cell" type="number" min={0} step="0.01" placeholder="TBD" defaultValue={r.cost_low ?? ""} onBlur={(e) => update(r, "cost_low", e.target.value)} />
                      –
                      <input className="cell" type="number" min={0} step="0.01" placeholder="TBD" defaultValue={r.cost_high ?? ""} onBlur={(e) => update(r, "cost_high", e.target.value)} />
                    </span>
                  )}
                </td>
                <td>
                  {r.derived ? (
                    <span className="small">{r.supplier_notes}</span>
                  ) : (
                    <input className="cell wide" defaultValue={r.supplier_notes} onBlur={(e) => update(r, "supplier_notes", e.target.value)} />
                  )}
                </td>
                <td>
                  {r.flags.map((f) => (
                    <Flag key={f} flag={f} />
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={8}>
                <strong>Total</strong>{" "}
                <span className="muted small">
                  ({bom.total.priced_items}/{bom.total.total_items} items priced{bom.total.complete ? "" : "; incomplete"})
                </span>
              </td>
              <td colSpan={3}>
                <strong>
                  {money(bom.total.low)} – {money(bom.total.high)}
                </strong>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}

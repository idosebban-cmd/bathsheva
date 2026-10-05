import { useCallback, useEffect, useState } from "react";
import { api, errorText, type CostItem, type CostLine, type CostReport } from "../api";
import { AssumptionBadge, UnverifiedBadge } from "../components/Badges";
import CostAudit from "../components/CostAudit";
import { CategoryBars, SensitivityBars, VolumeRanges, gbp } from "../components/CostCharts";
import { useProject } from "../components/useProject";

const CATEGORY_TEXT: Record<string, [string, string]> = {
  material: ["Material", "Raw material bought, including what's trimmed or machined away."],
  process: ["Making the parts", "Machine and operator time to form, machine or cut each part."],
  setup: ["Setup", "Setting up each job, shared across the batch."],
  finishing: ["Finishing", "Paint, lacquer, plating or polishing."],
  tooling: ["Tooling", "One-off tools and forms, shared across the batch."],
  bought_in: ["Bought-in parts", "LED, electronics, cable, fasteners and seals bought ready-made."],
  assembly: ["Assembly", "Putting the lamp together, wiring and testing it."],
  packaging: ["Packaging", "Retail box and inserts."],
};

export default function ManufacturingPage() {
  const { project } = useProject();
  const [report, setReport] = useState<CostReport | null>(null);
  const [items, setItems] = useState<CostItem[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [r, its] = await Promise.all([
        api.get<CostReport>(`/api/projects/${project.id}/costs`),
        api.get<CostItem[]>(`/api/projects/${project.id}/cost-items`),
      ]);
      setReport(r);
      setItems(its);
    } catch (e) {
      setError(errorText(e));
    }
  }, [project.id]);
  useEffect(() => {
    load();
  }, [load]);

  if (!report) return <p>{error || "Loading cost model…"}</p>;
  const u = report.unit_cost;
  const volumeAssumed = report.reference_basis.startsWith("assumed");
  const cats = Object.entries(report.categories).map(([k, v]) => ({
    label: CATEGORY_TEXT[k]?.[0] ?? k,
    help: CATEGORY_TEXT[k]?.[1] ?? "",
    ...v,
  }));

  return (
    <div className="stack manufacturing">
      <section className="card">
        <h2>Unit cost estimate</h2>
        <div className="hero-cost">
          <span className="hero-number">
            {gbp(u.low)} – {gbp(u.high)}
          </span>
          <span className="muted">
            per lamp at {report.reference_quantity.toLocaleString()} units {volumeAssumed && <AssumptionBadge title={report.reference_basis} />}
          </span>
        </div>
        <p className="small muted">
          Midpoint {gbp(u.mid)}. The range is the likely spread when each input varies independently. If every input landed at its
          worst end at once it would be {gbp(u.worst_low)} – {gbp(u.worst_high)}.
        </p>
        {report.uses_unverified_data && (
          <p className="notice small">
            <UnverifiedBadge /> All rates are <strong>model-generated and unverified</strong> (seed/cost/*.yaml). Low-confidence inputs
            are widened by {Math.round((report.spread.low ?? 0) * 100)}% and medium by {Math.round((report.spread.medium ?? 0) * 100)}%.
            Replace them with real quotes to narrow the range.
          </p>
        )}
        <ul className="small muted">
          {report.notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      </section>

      <div className="split">
        <section className="card">
          <h2>Cost by volume</h2>
          <VolumeRanges rows={report.volumes} referenceQuantity={report.reference_quantity} />
        </section>
        <section className="card">
          <h2>What drives the cost</h2>
          <p className="small muted">
            The {report.sensitivity.top.length} assumptions that move the unit cost most when each is changed by ±
            {Math.round(report.sensitivity.step * 100)}% (at {report.reference_quantity.toLocaleString()} units; {report.sensitivity.count}{" "}
            assumptions tested).
          </p>
          <SensitivityBars rows={report.sensitivity.top} step={report.sensitivity.step} />
        </section>
      </div>

      <section className="card">
        <CategoryBars rows={cats} />
      </section>

      <section className="card">
        <h2>Breakdown by part</h2>
        <p className="small muted">Per lamp at {report.reference_quantity.toLocaleString()} units. Each line explains how it was worked out.</p>
        {report.parts.map((p) => (
          <details key={p.part_id} className="part-cost">
            <summary>
              <strong>{p.name}</strong>
              {p.quantity > 1 && ` × ${p.quantity}`} · {p.process} · {p.material}
              {p.basis === "recommended" && <span className="muted small"> (recommended)</span>}
              <span className="part-cost-total">
                {gbp(p.low)} – {gbp(p.high)}
              </span>
            </summary>
            <LinesTable lines={p.lines} />
          </details>
        ))}
        {report.skipped.length > 0 && (
          <ul className="small muted">
            {report.skipped.map((s) => (
              <li key={s.name}>
                {s.name}: {s.reason}
              </li>
            ))}
          </ul>
        )}
        <h3>Product-level costs</h3>
        <LinesTable lines={report.product_lines} />
      </section>

      <ItemsEditor projectId={project.id} items={items} canLoadDefaults={report.can_load_defaults} onChanged={load} />

      {project.template && <CostAudit projectId={project.id} />}

      <section className="card">
        <details>
          <summary>
            <strong>Rates and assumptions used ({report.assumptions.length})</strong>
          </summary>
          <table className="small">
            <thead>
              <tr>
                <th>Assumption</th>
                <th>Range</th>
                <th>Widened for confidence</th>
                <th>Source</th>
                <th>Confidence</th>
                <th>Verified</th>
              </tr>
            </thead>
            <tbody>
              {report.assumptions.map((a) => (
                <tr key={a.key}>
                  <td>
                    {a.label}
                    <div className="muted">{a.group}</div>
                  </td>
                  <td className="nowrap-cell">
                    {a.low === a.high ? a.low : `${a.low} – ${a.high}`} {a.unit}
                  </td>
                  <td className="nowrap-cell">
                    {a.widened[0]} – {a.widened[1]} {a.unit}
                  </td>
                  <td>{a.source}</td>
                  <td>{a.confidence}</td>
                  <td>{a.verified ? "yes" : <UnverifiedBadge />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </section>
    </div>
  );
}

function LinesTable({ lines }: { lines: CostLine[] }) {
  return (
    <table className="small cost-lines">
      <thead>
        <tr>
          <th>Line</th>
          <th>How it's worked out</th>
          <th>Per lamp</th>
        </tr>
      </thead>
      <tbody>
        {lines.map((l, i) => (
          <tr key={i}>
            <td className="nowrap-cell">
              {l.part_id === null ? l.label : CATEGORY_TEXT[l.category]?.[0] ?? l.category}
              {l.unverified && (
                <div>
                  <UnverifiedBadge title={`${l.confidence} confidence`} />
                </div>
              )}
            </td>
            <td>{l.explanation}</td>
            <td className="nowrap-cell">
              {gbp(l.low)} – {gbp(l.high)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Editing one end past the other moves both, so low <= high always holds. */
function priceChange(it: CostItem, end: "low" | "high", value: number | null): Partial<CostItem> {
  if (end === "low") {
    return value !== null && it.unit_cost_high !== null && value > it.unit_cost_high
      ? { unit_cost_low: value, unit_cost_high: value }
      : { unit_cost_low: value };
  }
  return value !== null && it.unit_cost_low !== null && value < it.unit_cost_low
    ? { unit_cost_low: value, unit_cost_high: value }
    : { unit_cost_high: value };
}

const KIND_LABEL = { bought_in: "Bought-in", assembly: "Assembly", packaging: "Packaging", other: "Other" };

function ItemsEditor({
  projectId,
  items,
  canLoadDefaults,
  onChanged,
}: {
  projectId: number;
  items: CostItem[];
  canLoadDefaults: boolean;
  onChanged: () => Promise<void>;
}) {
  const [error, setError] = useState("");
  const num = (v: string) => (v.trim() === "" ? null : Number(v));

  async function patch(item: CostItem, changes: Partial<CostItem>) {
    setError("");
    try {
      await api.patch(`/api/projects/${projectId}/cost-items/${item.id}`, changes);
      await onChanged();
    } catch (e) {
      setError(errorText(e));
    }
  }
  async function add() {
    setError("");
    try {
      await api.post(`/api/projects/${projectId}/cost-items`, { name: "New item", quantity: 1, unit_cost_low: 0, unit_cost_high: 0 });
      await onChanged();
    } catch (e) {
      setError(errorText(e));
    }
  }
  async function remove(item: CostItem) {
    await api.del(`/api/projects/${projectId}/cost-items/${item.id}`);
    await onChanged();
  }
  async function reset() {
    if (items.length && !confirm("Replace all items with the template defaults for the current power type?")) return;
    await api.post(`/api/projects/${projectId}/cost-items/reset`);
    await onChanged();
  }

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>Bought-in parts, assembly and packaging</h2>
        <div className="row">
          {canLoadDefaults && <button onClick={reset}>{items.length ? "Reset to template defaults" : "Load template defaults"}</button>}
          <button onClick={add}>+ Add item</button>
        </div>
      </div>
      <p className="small muted">
        Editable assumptions. Changing a price marks it as your figure (source "user"). Tick verified once it comes from a real quote:
        verified values are not widened. Minute-based items use the seeded labour rate.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="table-wrap">
        <table className="small">
          <thead>
            <tr>
              <th>Type</th>
              <th>Item</th>
              <th>Qty</th>
              <th>Unit cost £ (low – high)</th>
              <th>Source</th>
              <th>Confidence</th>
              <th>Verified</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={`${it.id}-${it.source}-${it.unit_cost_low}-${it.unit_cost_high}-${it.quantity}`}>
                <td>{KIND_LABEL[it.kind]}</td>
                <td>
                  <input className="cell wide" defaultValue={it.name} onBlur={(e) => e.target.value !== it.name && patch(it, { name: e.target.value })} />
                  {it.notes && <div className="muted">{it.notes}</div>}
                </td>
                <td className="nowrap-cell">
                  <input
                    className="cell"
                    type="number"
                    min={0}
                    step="any"
                    defaultValue={it.quantity}
                    onBlur={(e) => Number(e.target.value) !== it.quantity && patch(it, { quantity: Number(e.target.value) })}
                  />{" "}
                  {it.unit}
                </td>
                <td className="nowrap-cell">
                  {it.unit === "min" && it.unit_cost_low === null ? (
                    <span className="muted">labour rate</span>
                  ) : (
                    <>
                      <input
                        className="cell"
                        type="number"
                        min={0}
                        step="0.01"
                        defaultValue={it.unit_cost_low ?? ""}
                        onBlur={(e) => num(e.target.value) !== it.unit_cost_low && patch(it, priceChange(it, "low", num(e.target.value)))}
                      />{" "}
                      –{" "}
                      <input
                        className="cell"
                        type="number"
                        min={0}
                        step="0.01"
                        defaultValue={it.unit_cost_high ?? ""}
                        onBlur={(e) => num(e.target.value) !== it.unit_cost_high && patch(it, priceChange(it, "high", num(e.target.value)))}
                      />
                    </>
                  )}
                </td>
                <td>{it.source}</td>
                <td>
                  <select value={it.confidence} onChange={(e) => patch(it, { confidence: e.target.value as CostItem["confidence"] })}>
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </select>
                </td>
                <td>
                  <label className="checkbox">
                    <input type="checkbox" checked={it.verified} onChange={(e) => patch(it, { verified: e.target.checked })} />
                    {!it.verified && <UnverifiedBadge />}
                  </label>
                </td>
                <td>
                  <button className="link danger" onClick={() => remove(it)}>
                    delete
                  </button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={8} className="muted">
                  No items yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

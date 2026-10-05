import { useState, type MouseEvent, type ReactNode } from "react";
import type { CostRange, SensitivityRow } from "../api";
import { UnverifiedBadge } from "./Badges";

/** "£6", "£47.5/hr", "0.025 min/cm³" */
export function formatValue(value: number, unit: string): string {
  const v = value.toLocaleString("en-GB", { maximumFractionDigits: 3 });
  if (unit.startsWith("£")) return `£${v}${unit.slice(1)}`;
  return `${v} ${unit}`.trim();
}

export const gbp = (v: number) => `£${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** Minimal hover tooltip: one per chart, follows the pointer. */
function useTooltip() {
  const [tip, setTip] = useState<{ x: number; y: number; content: ReactNode } | null>(null);
  const bind = (content: ReactNode) => ({
    onMouseMove: (e: MouseEvent) => setTip({ x: e.clientX, y: e.clientY, content }),
    onMouseLeave: () => setTip(null),
  });
  const node = tip ? (
    <div className="viz-tooltip" style={{ left: tip.x + 12, top: tip.y + 12 }} role="tooltip">
      {tip.content}
    </div>
  ) : null;
  return { bind, node };
}

/** Unit cost range per volume on one shared scale: bar = range, tick = midpoint. */
export function VolumeRanges({ rows, referenceQuantity }: { rows: CostRange[]; referenceQuantity: number }) {
  const { bind, node } = useTooltip();
  const max = Math.max(...rows.map((r) => r.high)) * 1.05 || 1;
  const pct = (v: number) => `${(v / max) * 100}%`;
  return (
    <div className="viz-root">
      <table className="viz-table">
        <thead>
          <tr>
            <th>Quantity</th>
            <th>Unit cost (likely range)</th>
            <th className="viz-col">Range</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.quantity} className={r.quantity === referenceQuantity ? "viz-ref" : ""}>
              <td>
                {r.quantity.toLocaleString()} units
                {r.is_project_volume && <span className="badge badge-status-edited">your volume</span>}
              </td>
              <td>
                <strong>
                  {gbp(r.low)} – {gbp(r.high)}
                </strong>
                <div className="muted small">midpoint {gbp(r.mid)}</div>
              </td>
              <td className="viz-col">
                <div
                  className="range-track"
                  {...bind(
                    <>
                      <strong>{r.quantity.toLocaleString()} units</strong>
                      <div>
                        Likely {gbp(r.low)} – {gbp(r.high)} (mid {gbp(r.mid)})
                      </div>
                      <div className="muted">
                        Every input at its worst: {gbp(r.worst_low)} – {gbp(r.worst_high)}
                      </div>
                    </>,
                  )}
                >
                  <div className="range-bar" style={{ left: pct(r.low), width: `calc(${pct(r.high - r.low)})` }} />
                  <div className="range-mid" style={{ left: pct(r.mid) }} />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="viz-axis muted small">
        <span>£0</span>
        <span>{gbp(max)}</span>
      </div>
      {node}
    </div>
  );
}

/** Top cost drivers: bar length = unit-cost swing when the assumption moves ±step. */
export function SensitivityBars({ rows, step }: { rows: SensitivityRow[]; step: number }) {
  const { bind, node } = useTooltip();
  const max = Math.max(...rows.map((r) => Math.abs(r.swing))) || 1;
  const pctStep = Math.round(step * 100);
  return (
    <div className="viz-root sens">
      {rows.map((r, i) => (
        <div className="sens-row" key={r.key}>
          <div className="sens-label">
            <span className="sens-rank">{i + 1}</span>
            <div>
              <div>{r.label}</div>
              <div className="muted small">
                now {formatValue(r.value, r.unit)} · {r.group}{" "}
                {!r.verified && <UnverifiedBadge title={`${r.source}, ${r.confidence} confidence`} />}
              </div>
            </div>
          </div>
          <div
            className="sens-track"
            {...bind(
              <>
                <strong>{r.label}</strong>
                <div>
                  {pctStep}% lower → {gbp(r.cost_down)} per unit
                </div>
                <div>
                  {pctStep}% higher → {gbp(r.cost_up)} per unit
                </div>
              </>,
            )}
          >
            <div className="sens-bar" style={{ width: `${(Math.abs(r.swing) / max) * 100}%` }} />
            <span className="sens-value">
              ±{gbp(Math.abs(r.swing))} <span className="muted">({r.swing_pct}%)</span>
            </span>
          </div>
        </div>
      ))}
      {node}
    </div>
  );
}

/** Share of the midpoint unit cost by category. */
export function CategoryBars({ rows }: { rows: { label: string; low: number; mid: number; high: number; help: string }[] }) {
  const { bind, node } = useTooltip();
  const totalMid = rows.reduce((s, r) => s + r.mid, 0) || 1;
  const max = Math.max(...rows.map((r) => r.mid)) || 1;
  return (
    <div className="viz-root">
      <table className="viz-table">
        <thead>
          <tr>
            <th>Where the money goes</th>
            <th>Per unit</th>
            <th className="viz-col">Share of midpoint</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <td>
                {r.label}
                <div className="muted small">{r.help}</div>
              </td>
              <td className="nowrap-cell">
                {gbp(r.low)} – {gbp(r.high)}
              </td>
              <td className="viz-col">
                <div className="share-track" {...bind(<>{r.label}: {gbp(r.mid)} midpoint, {((r.mid / totalMid) * 100).toFixed(0)}% of unit cost</>)}>
                  <div className="share-bar" style={{ width: `${(r.mid / max) * 100}%` }} />
                  <span className="share-value">{((r.mid / totalMid) * 100).toFixed(0)}%</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {node}
    </div>
  );
}

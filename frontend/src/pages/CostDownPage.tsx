import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { api, errorText } from "../api";
import { SafetyBadge, UnverifiedBadge } from "../components/Badges";
import { gbp } from "../components/CostCharts";
import { useProject } from "../components/useProject";

// ---- API shapes (local to this page) ----------------------------------------------

type Status = "pass" | "close" | "fail";
interface TargetAssess {
  target: number;
  status: Status;
  gap: number;
}
interface Range {
  quantity: number;
  low: number;
  mid: number;
  high: number;
  raw_mid?: number;
}
interface SelItem {
  key: string;
  letter: string;
  label: string;
  option: number | null;
  option_label: string;
  premium_impact: string;
}
interface Flag {
  kind: string;
  message: string;
  part?: string;
  scenario?: string;
}
interface Pricing {
  values: Record<string, number>;
  meta: Record<string, { value: number; default: number; edited: boolean; source: string; confidence: string; verified: boolean; plain_language: string }>;
  targets: {
    standard: Record<string, number>;
    bands: Record<"dtc" | "retail", { target: number; low: number; high: number }>;
    premium: Record<string, number>;
  } | null;
}
interface SummaryRow {
  label: string;
  quantity: number;
  region: string;
  region_name: string;
  selection: SelItem[];
  cost: Range;
  targets: Record<"dtc" | "retail", TargetAssess>;
  flags: Flag[];
  tier?: string;
  same_as?: string | null;
  power?: string;
  power_label?: string;
}
interface PricePoint {
  retail_inc_vat: number;
  retail_ex_vat: number;
  wholesale: number;
  dtc: number;
  retail: number;
}
interface PricePointRow {
  quantity: number;
  label: string;
  tier: string;
  region_name: string;
  selection: string[];
  cost: { low: number; mid: number; high: number };
  by_price: Record<string, Record<"dtc" | "retail", TargetAssess>>;
}
interface StackLine {
  key: string;
  label: string;
  amount: number;
}
interface PriceStack {
  factory_cost: number;
  quantity: number;
  break_even_retail: number;
  target_retail: number;
  lines: StackLine[];
  at_planned?: { retail: number; profit: number; profit_pct: number };
}
interface EditionRow {
  edition: string;
  power: string;
  power_label: string;
  quantity: number;
  region_name: string;
  cost: Range;
  targets: Record<"dtc" | "retail", TargetAssess>;
  selection: string[];
  price_stack: PriceStack;
}
interface Summary {
  editions?: { rows: EditionRow[]; label: string | null; notes: string[] };
  price_points?: { points: PricePoint[]; rows: PricePointRow[]; power_label: string; notes: string[] };
  rows: SummaryRow[];
  power_options?: { key: string; label: string; scenario: string | null }[];
  premium: { label: string; retail: number; targets: Record<string, number>; rows: SummaryRow[] };
  notes: string[];
}
interface Scenario {
  key: string;
  letter: string;
  label: string;
  design_change: string;
  premium_impact: string;
  conflicts: string[];
  flags: Flag[];
  tradeoffs: Record<string, string>;
  options: { option: number; label: string; saving: Record<string, number>; allowed?: boolean; excluded_reason?: string }[];
}
interface RegionInfo {
  key: string;
  name: string;
  lead_time_note: string;
  verified: boolean;
  saving: Record<string, number>;
  multipliers: Record<string, number[]>;
}
interface Catalog {
  scenarios: Scenario[];
  regions: RegionInfo[];
  current: Record<string, number>;
}
interface Evaluation {
  selection: SelItem[];
  region: string;
  volumes: (Range & { current_mid: number; saving: number; targets?: Record<"dtc" | "retail", TargetAssess> })[];
  marginal: (SelItem & { saving: Record<string, number> })[];
  flags: Flag[];
  design_changes: { part: string; text: string }[];
  removed: string[];
}
interface Route {
  process_key: string;
  process: string;
  material_key: string;
  material: string;
  is_current: boolean;
  viable: boolean;
  costs: Record<string, Range>;
  tooling: { low: number; high: number };
  design_changes: string[];
  extra_items: string[];
  flags: Flag[];
  crossovers: { vs: string; quantity: number; text: string }[];
  tradeoffs: Record<string, string>;
}
interface Routes {
  volumes: number[];
  parts: { part_id: number; name: string; current: string; routes: Route[]; cheapest_by_volume: Record<string, string> }[];
}
interface ScenarioSet {
  id: number;
  name: string;
  changes: { key: string; option: number | null }[];
  region: string;
}

const TRADEOFF_LABELS: Record<string, string> = {
  cost: "Cost",
  finish: "Finish quality",
  weight: "Weight",
  premium: "Premium feel",
  lead_time: "Lead time",
  tooling: "Tooling commitment",
};

function StatusChip({ a, name }: { a: TargetAssess; name: string }) {
  const text = a.status === "pass" ? "Pass" : a.status === "close" ? "Close" : "Fail";
  return (
    <span className={`status status-${a.status}`} title={`${name} target ${gbp(a.target)}`}>
      <span aria-hidden>{a.status === "pass" ? "✓" : a.status === "close" ? "≈" : "✗"}</span> {text}
      <span className="status-gap">{a.gap > 0 ? `+${gbp(a.gap)}` : `−${gbp(-a.gap)}`}</span>
    </span>
  );
}

function ImpactBadge({ impact }: { impact: string }) {
  if (impact === "none") return <span className="badge badge-status-accepted">keeps premium look</span>;
  if (impact === "slight") return <span className="badge badge-unverified">slight compromise</span>;
  return <span className="badge badge-safety">changes the design</span>;
}

function Changes({ sel, region }: { sel: SelItem[]; region?: string }) {
  if (!sel.length && (!region || region === "United Kingdom")) return <span className="muted">No changes, made in the UK</span>;
  return (
    <span>
      {sel.map((s) => (
        <span key={s.key} className="change-pill" title={s.label}>
          {s.letter}
          {s.option_label ? `: ${s.option_label}` : ""}
        </span>
      ))}
      {region && <span className="change-pill region-pill">{region}</span>}
    </span>
  );
}

export default function CostDownPage() {
  const { project } = useProject();
  const [pricing, setPricing] = useState<Pricing | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [routes, setRoutes] = useState<Routes | null>(null);
  const [error, setError] = useState("");

  const loadAll = useCallback(async () => {
    setError("");
    try {
      const [p, s, c, r] = await Promise.all([
        api.get<Pricing>(`/api/projects/${project.id}/pricing`),
        api.get<Summary>(`/api/projects/${project.id}/cost-down/summary`),
        api.get<Catalog>(`/api/projects/${project.id}/scenarios`),
        api.get<Routes>(`/api/projects/${project.id}/routes`),
      ]);
      setPricing(p);
      setSummary(s);
      setCatalog(c);
      setRoutes(r);
    } catch (e) {
      setError(errorText(e));
    }
  }, [project.id]);
  useEffect(() => {
    loadAll();
  }, [loadAll]);

  if (error) return <p className="error">{error}</p>;
  if (!pricing || !summary || !catalog || !routes) return <p>Loading cost-down analysis…</p>;

  return (
    <div className="stack costdown">
      <section className="card">
        <h2>Cost-down</h2>
        <p className="small">
          How far the current design is from the target factory cost, and which process routes and design changes close the gap. Nothing
          here changes the design until you select a route; scenarios are what-ifs.
        </p>
        <p className="notice small">
          <UnverifiedBadge /> Most rates, the regional multipliers and channel economics are <strong>model-generated</strong>; some prices are researched distributor or retail prices adjusted for volume. All are <strong>unverified</strong>. Use
          this to decide which quotes to get first, not as a price.
        </p>
      </section>
      <TargetsCard pricing={pricing} projectId={project.id} onSaved={loadAll} />
      <PriceStackCard pricing={pricing} summary={summary} projectId={project.id} onSaved={loadAll} />
      <SummaryCard summary={summary} />
      <ScenarioBuilder projectId={project.id} catalog={catalog} />
      <RoutesCard projectId={project.id} routes={routes} onChanged={loadAll} />
    </div>
  );
}

// ---- Targets -----------------------------------------------------------------------

const PRICE_FIELDS: [string, string, "money" | "pct"][] = [
  ["retail_price", "Target retail price (inc. VAT)", "money"],
  ["retail_low", "Retail range: low", "money"],
  ["retail_high", "Retail range: high", "money"],
  ["premium_retail", "Premium brass edition retail", "money"],
  ["vat_rate", "VAT", "pct"],
  ["dtc_factory_share", "DTC: factory cost as share of ex-VAT price", "pct"],
  ["retailer_margin", "Retailer margin (share of ex-VAT price)", "pct"],
  ["wholesale_factory_share", "Retail channel: factory cost as share of wholesale", "pct"],
  ["close_band", "'Close' band above target", "pct"],
];

function TargetsCard({ pricing, projectId, onSaved }: { pricing: Pricing; projectId: number; onSaved: () => Promise<void> }) {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const t = pricing.targets;

  async function save() {
    const changes: Record<string, number> = {};
    for (const [k, v] of Object.entries(draft)) {
      const [, , kind] = PRICE_FIELDS.find((f) => f[0] === k)!;
      changes[k] = kind === "pct" ? Number(v) / 100 : Number(v);
    }
    setStatus("Saving…");
    try {
      await api.put(`/api/projects/${projectId}/pricing`, changes);
      setDraft({});
      setStatus("Saved");
      await onSaved();
    } catch (e) {
      setStatus(errorText(e));
    }
  }

  return (
    <section className="card">
      <h2>Price and target factory cost</h2>
      {t && (
        <div className="target-tiles">
          <div className="tile-target">
            <div className="muted small">Direct to consumer</div>
            <div className="tile-big">{gbp(t.bands.dtc.target)}</div>
            <div className="muted small">
              band {gbp(t.bands.dtc.low)} – {gbp(t.bands.dtc.high)} for retail {gbp(pricing.values.retail_low)} – {gbp(pricing.values.retail_high)}
            </div>
          </div>
          <div className="tile-target">
            <div className="muted small">Through retailers</div>
            <div className="tile-big">{gbp(t.bands.retail.target)}</div>
            <div className="muted small">
              band {gbp(t.bands.retail.low)} – {gbp(t.bands.retail.high)}; wholesale {gbp(t.standard.wholesale)}
            </div>
          </div>
          <div className="tile-target">
            <div className="muted small">Premium brass edition ({gbp(pricing.values.premium_retail)})</div>
            <div className="tile-big">
              {gbp(t.premium.dtc)} / {gbp(t.premium.retail)}
            </div>
            <div className="muted small">DTC / retail targets</div>
          </div>
        </div>
      )}
      <details>
        <summary>Edit pricing assumptions</summary>
        <div className="grid">
          {PRICE_FIELDS.map(([k, label, kind]) => {
            const m = pricing.meta[k];
            const shown = kind === "pct" ? +(m.value * 100).toFixed(2) : m.value;
            return (
              <label key={k} className="field">
                <span>
                  {label} {!m.verified && <UnverifiedBadge title={`${m.source}, ${m.confidence} confidence`} />}
                  {m.edited && <span className="badge badge-status-edited">yours</span>}
                </span>
                <input
                  type="number"
                  step="any"
                  value={draft[k] ?? String(shown)}
                  onChange={(e) => setDraft({ ...draft, [k]: e.target.value })}
                />
                {kind === "pct" && <span className="muted small">%</span>}
                {m.plain_language && <span className="muted small">{m.plain_language}</span>}
              </label>
            );
          })}
        </div>
        <div className="row">
          <button className="primary" disabled={!Object.keys(draft).length} onClick={save}>
            Save pricing
          </button>
          <span className="muted small">{status}</span>
        </div>
      </details>
    </section>
  );
}

// ---- DTC price stack -----------------------------------------------------------------

const STACK_FIELDS: [string, string, "money" | "pct"][] = [
  ["vat_rate", "VAT", "pct"],
  ["stack_freight", "Inbound handling and storage (£ per lamp)", "money"],
  ["stack_delivery", "Delivery to customer (£ per order)", "money"],
  ["stack_payment_pct", "Payment fees (% of price paid)", "pct"],
  ["stack_payment_fixed", "Payment fee per order (£)", "money"],
  ["stack_returns_pct", "Returns and warranty (% of ex-VAT price)", "pct"],
  ["stack_marketing", "Marketing per sale (£)", "money"],
  ["stack_one_off", "Other one-off launch costs (£ total, shared over the batch)", "money"],
  ["stack_profit_pct", "Profit target (% of ex-VAT price)", "pct"],
];

function PriceStackCard({ pricing, summary, projectId, onSaved }: {
  pricing: Pricing; summary: Summary; projectId: number; onSaved: () => Promise<void>;
}) {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const rows = summary.editions?.rows ?? [];
  const powers = Array.from(new Set(rows.map((r) => r.power)));
  const [power, setPower] = useState<string>(powers[0] ?? "A");
  const [open, setOpen] = useState<string | null>(null);
  if (!rows.length) return null;
  const shown = rows.filter((r) => r.power === power);
  const planned = pricing.values.retail_price;

  async function save() {
    const changes: Record<string, number> = {};
    for (const [k, v] of Object.entries(draft)) {
      const [, , kind] = STACK_FIELDS.find((f) => f[0] === k)!;
      changes[k] = kind === "pct" ? Number(v) / 100 : Number(v);
    }
    setStatus("Saving…");
    try {
      await api.put(`/api/projects/${projectId}/pricing`, changes);
      setDraft({});
      setStatus("Saved");
      await onSaved();
    } catch (e) {
      setStatus(errorText(e));
    }
  }

  return (
    <section className="card">
      <h2>DTC price stack: the retail price each version needs</h2>
      <p className="small">
        Selling direct, the retail price has to cover VAT, the factory cost and every line below. <b>Break-even</b> covers them with no
        profit; <b>for profit target</b> also keeps the profit share. Costs are the best configuration with no compromise to the look
        (full detail) and the same search for the simplified premium version.
      </p>
      {powers.length > 1 && (
        <div className="row small">
          Power:{" "}
          {powers.map((pk) => (
            <button key={pk} className={`link${pk === power ? " active" : ""}`} onClick={() => setPower(pk)}>
              {rows.find((r) => r.power === pk)?.power_label ?? pk}
            </button>
          ))}
        </div>
      )}
      <table className="summary-table">
        <thead>
          <tr>
            <th>Version</th>
            <th>Units</th>
            <th>Made in</th>
            <th className="num">Factory cost</th>
            <th className="num">Break-even retail</th>
            <th className="num">Retail for profit target</th>
            <th className="num">Profit at {gbp(planned)}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {shown.map((r) => {
            const id = `${r.edition}-${r.quantity}`;
            const ps = r.price_stack;
            return (
              <Fragment key={id}>
                <tr>
                  <td>{r.edition}</td>
                  <td>{r.quantity.toLocaleString()}</td>
                  <td>{r.region_name}</td>
                  <td className="num">
                    {gbp(r.cost.mid)} <span className="muted small">({gbp(r.cost.low)}–{gbp(r.cost.high)})</span>
                  </td>
                  <td className="num">{gbp(ps.break_even_retail)}</td>
                  <td className="num"><b>{gbp(ps.target_retail)}</b></td>
                  <td className="num">
                    {ps.at_planned
                      ? <span className={ps.at_planned.profit < 0 ? "error" : ""}>{gbp(ps.at_planned.profit)} ({(ps.at_planned.profit_pct * 100).toFixed(1)}%)</span>
                      : "—"}
                  </td>
                  <td>
                    <button className="link" onClick={() => setOpen(open === id ? null : id)}>{open === id ? "Hide" : "Stack"}</button>
                  </td>
                </tr>
                {open === id && (
                  <tr>
                    <td colSpan={8}>
                      <table className="small">
                        <tbody>
                          {ps.lines.map((l) => (
                            <tr key={l.key}>
                              <td>{l.label}</td>
                              <td className="num">{gbp(l.amount)}</td>
                            </tr>
                          ))}
                          <tr>
                            <td><b>Retail price (inc. VAT)</b></td>
                            <td className="num"><b>{gbp(ps.target_retail)}</b></td>
                          </tr>
                        </tbody>
                      </table>
                      {r.selection.length > 0 && <p className="muted small">Changes: {r.selection.join("; ")}</p>}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
      <ul className="muted small">
        {(summary.editions?.notes ?? []).map((n) => <li key={n}>{n}</li>)}
      </ul>
      <details>
        <summary>Edit the price stack</summary>
        <div className="grid">
          {STACK_FIELDS.map(([k, label, kind]) => {
            const m = pricing.meta[k];
            if (!m) return null;
            const val = kind === "pct" ? +(m.value * 100).toFixed(2) : m.value;
            return (
              <label key={k} className="field">
                <span>
                  {label} {!m.verified && <UnverifiedBadge title={`${m.source}, ${m.confidence} confidence`} />}
                  {m.edited && <span className="badge badge-status-edited">yours</span>}
                </span>
                <input type="number" step="any" value={draft[k] ?? String(val)}
                  onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} />
                {kind === "pct" && <span className="muted small">%</span>}
                {m.plain_language && <span className="muted small">{m.plain_language}</span>}
              </label>
            );
          })}
        </div>
        <div className="row">
          <button className="primary" disabled={!Object.keys(draft).length} onClick={save}>Save price stack</button>
          <span className="muted small">{status}</span>
        </div>
      </details>
    </section>
  );
}

// ---- Product summary --------------------------------------------------------------

function SummaryTable({ rows, targetLabel }: { rows: SummaryRow[]; targetLabel: string }) {
  return (
    <table className="summary-table">
      <thead>
        <tr>
          <th>Units</th>
          <th>Configuration</th>
          <th>Unit cost (likely)</th>
          <th>DTC {targetLabel}</th>
          <th>Retail {targetLabel}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className={r.tier === "current" ? "row-current" : ""}>
            <td>{r.quantity.toLocaleString()}</td>
            <td>
              <strong>{r.label}</strong>
              {r.same_as ? (
                <div className="muted small">Same as “{r.same_as}”.</div>
              ) : (
                <div className="small">
                  <Changes sel={r.selection} region={r.region !== "uk" ? r.region_name : undefined} />
                </div>
              )}
              {r.flags.some((f) => f.kind === "safety") && <SafetyBadge title="Includes a change whose safety must be verified" />}
              {r.flags.some((f) => f.kind === "compliance") && <span className="badge badge-unverified">compliance check</span>}
            </td>
            <td className="nowrap-cell">
              <strong>{gbp(r.cost.mid)}</strong>
              <div className="muted small">
                {gbp(r.cost.low)} – {gbp(r.cost.high)}
              </div>
              {r.cost.raw_mid !== undefined && r.cost.raw_mid !== r.cost.mid && (
                <div className="muted small" title="Every price at its researched basis (small-quantity distributor / retail), no volume discount">
                  raw researched {gbp(r.cost.raw_mid)}
                </div>
              )}
            </td>
            <td>
              <StatusChip a={r.targets.dtc} name="DTC" />
            </td>
            <td>
              <StatusChip a={r.targets.retail} name="Retail" />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PricePointsCard({ pp }: { pp: NonNullable<Summary["price_points"]> }) {
  return (
    <section className="card">
      <h2>Retail price points: DTC and retail-channel targets</h2>
      <table className="small">
        <thead>
          <tr>
            <th>Retail inc. VAT</th>
            <th>Ex VAT</th>
            <th>DTC factory target</th>
            <th>Wholesale</th>
            <th>Retail-channel factory target</th>
          </tr>
        </thead>
        <tbody>
          {pp.points.map((p) => (
            <tr key={p.retail_inc_vat}>
              <td><strong>{gbp(p.retail_inc_vat)}</strong></td>
              <td>{gbp(p.retail_ex_vat)}</td>
              <td>{gbp(p.dtc)}</td>
              <td>{gbp(p.wholesale)}</td>
              <td>{gbp(p.retail)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3 style={{ marginTop: "0.8rem" }}>Current and best configurations against each price ({pp.power_label})</h3>
      <table className="small">
        <thead>
          <tr>
            <th>Qty</th>
            <th>Configuration</th>
            <th>Unit cost</th>
            {pp.points.map((p) => (
              <th key={p.retail_inc_vat}>{gbp(p.retail_inc_vat)}: DTC / retail</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {pp.rows.map((r, i) => (
            <tr key={i}>
              <td>{r.quantity.toLocaleString()}</td>
              <td>
                {r.label}
                <div className="muted">{r.region_name}{r.selection.length ? ` · ${r.selection.join(" · ")}` : ""}</div>
              </td>
              <td className="nowrap-cell">
                <strong>{gbp(r.cost.mid)}</strong>
                <div className="muted">{gbp(r.cost.low)} – {gbp(r.cost.high)}</div>
              </td>
              {pp.points.map((p) => {
                const a = r.by_price[String(p.retail_inc_vat)];
                return (
                  <td key={p.retail_inc_vat}>
                    <StatusChip a={a.dtc} name="DTC" /> <StatusChip a={a.retail} name="Retail" />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="small muted">
        {pp.notes.map((n, i) => <li key={i}>{n}</li>)}
      </ul>
    </section>
  );
}

function SummaryCard({ summary }: { summary: Summary }) {
  return (
    <>
    {summary.price_points && <PricePointsCard pp={summary.price_points} />}
    <section className="card">
      <h2>Product view: current vs best combination</h2>
      {(summary.power_options ?? [{ key: "A", label: "", scenario: null }]).map((p) => (
        <div key={p.key}>
          {p.label && <h3 style={{ marginTop: "0.8rem" }}>Power option {p.label}</h3>}
          <SummaryTable rows={summary.rows.filter((r) => (r.power ?? "A") === p.key)} targetLabel="target" />
        </div>
      ))}
      <h3 style={{ marginTop: "1rem" }}>
        {summary.premium.label} at {gbp(summary.premium.retail)}
      </h3>
      <p className="small muted">
        Cream band and cap in brass, either plated or solid (polished, clear lacquer), compared with the premium edition's own
        targets.
      </p>
      {(summary.power_options ?? [{ key: "A", label: "", scenario: null }]).map((p) => (
        <div key={p.key}>
          {p.label && <h4>Power option {p.label}</h4>}
          <SummaryTable rows={summary.premium.rows.filter((r) => (r.power ?? "A") === p.key)} targetLabel="(premium)" />
        </div>
      ))}
      <ul className="small muted">
        {summary.notes.map((n, i) => (
          <li key={i}>{n}</li>
        ))}
      </ul>
    </section>
    </>
  );
}

// ---- Scenario builder --------------------------------------------------------------

function ScenarioBuilder({ projectId, catalog }: { projectId: number; catalog: Catalog }) {
  const [selected, setSelected] = useState<Record<string, number | null>>({});
  const [region, setRegion] = useState("uk");
  const [result, setResult] = useState<Evaluation | null>(null);
  const [sets, setSets] = useState<ScenarioSet[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const conflicts = useMemo(() => {
    const out = new Set<string>();
    for (const s of catalog.scenarios) if (s.key in selected) s.conflicts.forEach((c) => out.add(c));
    return out;
  }, [selected, catalog]);

  const changes = Object.entries(selected).map(([key, option]) => ({ key, option }));

  useEffect(() => {
    api.get<ScenarioSet[]>(`/api/projects/${projectId}/scenario-sets`).then(setSets, () => undefined);
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    api
      .post<Evaluation>(`/api/projects/${projectId}/scenarios/evaluate`, { changes, region })
      .then((r) => !cancelled && (setResult(r), setError("")))
      .catch((e) => !cancelled && setError(errorText(e)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, JSON.stringify(changes), region]);

  function toggle(key: string) {
    const next = { ...selected };
    if (key in next) delete next[key];
    else next[key] = null;
    setSelected(next);
  }

  async function saveSet() {
    try {
      await api.post(`/api/projects/${projectId}/scenario-sets`, { name, changes, region });
      setName("");
      setSets(await api.get<ScenarioSet[]>(`/api/projects/${projectId}/scenario-sets`));
    } catch (e) {
      setError(errorText(e));
    }
  }
  function loadSet(s: ScenarioSet) {
    setSelected(Object.fromEntries(s.changes.map((c) => [c.key, c.option])));
    setRegion(s.region);
  }
  async function deleteSet(s: ScenarioSet) {
    await api.del(`/api/projects/${projectId}/scenario-sets/${s.id}`);
    setSets(await api.get<ScenarioSet[]>(`/api/projects/${projectId}/scenario-sets`));
  }

  return (
    <section className="card">
      <h2>Design-change scenarios</h2>
      <p className="small muted">
        Tick changes to combine them. "Saving alone" is each change on its own against the current configuration (per lamp). Multi-option
        changes use the cheapest option unless you pick one.
      </p>
      <div className="scenario-layout">
        <div>
          {catalog.scenarios.map((s) => {
            const on = s.key in selected;
            const blocked = !on && conflicts.has(s.key);
            const bestOpt = s.options.reduce((a, b) => (b.saving["500"] > a.saving["500"] ? b : a));
            return (
              <div key={s.key} className={`scenario ${on ? "on" : ""} ${blocked ? "blocked" : ""}`}>
                <label className="scenario-head">
                  <input type="checkbox" checked={on} disabled={blocked} onChange={() => toggle(s.key)} />
                  <span className="scenario-letter">{s.letter}</span>
                  <span className="scenario-title">{s.label}</span>
                  <span className="scenario-saving nowrap-cell">
                    {bestOpt.saving["500"] >= 0 ? "−" : "+"}
                    {gbp(Math.abs(bestOpt.saving["500"]))} <span className="muted">@500</span>
                  </span>
                </label>
                <div className="scenario-body small">
                  <div className="scenario-tags">
                    <ImpactBadge impact={s.premium_impact} />
                    {s.flags.map((f, i) => (
                      <span key={i} className={f.kind === "safety" ? "badge badge-safety" : "badge badge-unverified"} title={f.message}>
                        {f.kind === "safety" ? "Safety: verify" : "Compliance: verify"}
                      </span>
                    ))}
                    {blocked && <span className="muted">conflicts with a selected change</span>}
                  </div>
                  <div>{s.design_change}</div>
                  {s.options.length > 1 && (
                    <div className="row">
                      <span className="muted">Option:</span>
                      <select
                        value={on ? (selected[s.key] ?? "auto") : "auto"}
                        disabled={!on}
                        onChange={(e) => setSelected({ ...selected, [s.key]: e.target.value === "auto" ? null : Number(e.target.value) })}
                      >
                        <option value="auto">Cheapest</option>
                        {s.options.map((o) => (
                          <option key={o.option} value={o.option} disabled={o.allowed === false} title={o.excluded_reason}>
                            {o.label} ({o.saving["500"] >= 0 ? "−" : "+"}
                            {gbp(Math.abs(o.saving["500"]))} @500){o.allowed === false ? " — excluded by design constraint" : ""}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                  <details>
                    <summary>Trade-offs</summary>
                    <dl className="tech">
                      <div>
                        <dt>Cost</dt>
                        <dd>
                          {s.options
                            .map(
                              (o) =>
                                `${o.label ? o.label + ": " : ""}${o.saving["500"] >= 0 ? "saves" : "adds"} ${gbp(Math.abs(o.saving["500"]))} at 500, ${gbp(
                                  Math.abs(o.saving["2000"]),
                                )} at 2,000`,
                            )
                            .join("; ")}
                        </dd>
                      </div>
                      {Object.entries(s.tradeoffs).map(([k, v]) => (
                        <div key={k}>
                          <dt>{TRADEOFF_LABELS[k] ?? k}</dt>
                          <dd>{v}</dd>
                        </div>
                      ))}
                      {s.flags.map((f, i) => (
                        <div key={`f${i}`}>
                          <dt>{f.kind === "safety" ? "Safety" : "Compliance"}</dt>
                          <dd>{f.message}</dd>
                        </div>
                      ))}
                    </dl>
                  </details>
                </div>
              </div>
            );
          })}
          <div className="scenario">
            <div className="scenario-head">
              <span className="scenario-letter">i</span>
              <span className="scenario-title">Manufacturing region</span>
              <select value={region} onChange={(e) => setRegion(e.target.value)}>
                {catalog.regions.map((r) => (
                  <option key={r.key} value={r.key}>
                    {r.name} ({r.saving["500"] >= 0 ? "−" : "+"}
                    {gbp(Math.abs(r.saving["500"]))} @500)
                  </option>
                ))}
              </select>
            </div>
            <div className="scenario-body small">
              <UnverifiedBadge title="Regional multipliers are model-generated" />{" "}
              {catalog.regions.find((r) => r.key === region)?.lead_time_note}
            </div>
          </div>
        </div>
        <div className="scenario-result">
          <h3>Selected combination</h3>
          {error && <p className="error">{error}</p>}
          {result && (
            <>
              <div className="table-wrap">
              <table className="small">
                <thead>
                  <tr>
                    <th>Units</th>
                    <th>Unit cost</th>
                    <th>Saving</th>
                    <th>DTC</th>
                    <th>Retail</th>
                  </tr>
                </thead>
                <tbody>
                  {result.volumes.map((v) => (
                    <tr key={v.quantity}>
                      <td>{v.quantity.toLocaleString()}</td>
                      <td className="nowrap-cell">
                        <strong>{gbp(v.mid)}</strong>
                        <div className="muted">
                          {gbp(v.low)} – {gbp(v.high)}
                        </div>
                      </td>
                      <td className="nowrap-cell">{gbp(v.saving)}</td>
                      <td>{v.targets && <StatusChip a={v.targets.dtc} name="DTC" />}</td>
                      <td>{v.targets && <StatusChip a={v.targets.retail} name="Retail" />}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              {result.marginal.length > 0 && (
                <>
                  <h4>What each change saves in this combination</h4>
                  <ul className="small">
                    {result.marginal.map((m) => (
                      <li key={m.key}>
                        <strong>
                          {m.letter}. {m.label}
                        </strong>
                        {m.option_label && ` (${m.option_label})`}: {gbp(m.saving["500"])} at 500, {gbp(m.saving["2000"])} at 2,000
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {result.design_changes.length > 0 && (
                <>
                  <h4>Design changes needed</h4>
                  <ul className="small">
                    {result.design_changes.map((d, i) => (
                      <li key={i}>
                        <strong>{d.part}:</strong> {d.text}
                      </li>
                    ))}
                    {result.removed.map((r) => (
                      <li key={r}>
                        <strong>{r}:</strong> removed.
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {result.flags.length > 0 && (
                <div className="safety-box small">
                  <strong>Needs verification</strong>
                  <ul>
                    {result.flags.map((f, i) => (
                      <li key={i}>
                        {f.part ? `${f.part}: ` : ""}
                        {f.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="row">
                <input placeholder="Save this combination as…" value={name} onChange={(e) => setName(e.target.value)} />
                <button disabled={!name.trim()} onClick={saveSet}>
                  Save
                </button>
              </div>
              {sets.length > 0 && (
                <ul className="small">
                  {sets.map((s) => (
                    <li key={s.id}>
                      <button className="link" onClick={() => loadSet(s)}>
                        {s.name}
                      </button>{" "}
                      <span className="muted">
                        ({s.changes.map((c) => catalog.scenarios.find((x) => x.key === c.key)?.letter).join(", ") || "no changes"};{" "}
                        {catalog.regions.find((r) => r.key === s.region)?.name})
                      </span>
                      <button className="link danger" onClick={() => deleteSet(s)}>
                        delete
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}

// ---- Process routes ----------------------------------------------------------------

function RoutesCard({ projectId, routes, onChanged }: { projectId: number; routes: Routes; onChanged: () => Promise<void> }) {
  const [error, setError] = useState("");
  const vols = routes.volumes.map(String);

  async function select(partId: number, r: Route) {
    const reason = prompt(`Why choose ${r.process} (${r.material}) for this part? This is recorded as an engineering decision.`);
    if (!reason?.trim()) return;
    try {
      await api.post(`/api/projects/${projectId}/parts/${partId}/route`, { process_key: r.process_key, material_key: r.material_key, reason });
      await onChanged();
    } catch (e) {
      setError(errorText(e));
    }
  }

  return (
    <section className="card">
      <h2>Process routes per part</h2>
      <p className="small muted">
        Every process the rules engine considers viable, costed per lamp (part plus any extra parts the route needs). Selecting a route
        records a decision and updates cost, BOM and DFM. It does not change the CAD; parts whose route needs a design change are flagged
        until the CAD is updated.
      </p>
      {error && <p className="error">{error}</p>}
      {routes.parts.map((p) => (
        <details key={p.part_id} className="route-part" open={p.name === "Base"}>
          <summary>
            <strong>{p.name}</strong> · now {p.current}
            <span className="muted small"> · cheapest at 500: {p.cheapest_by_volume["500"]}</span>
          </summary>
          <div className="table-wrap">
            <table className="small">
              <thead>
                <tr>
                  <th>Process / material</th>
                  {vols.map((q) => (
                    <th key={q}>{Number(q).toLocaleString()} units</th>
                  ))}
                  <th>Tooling</th>
                  <th>Crossovers</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {p.routes.map((r) => (
                  <tr key={`${r.process_key}-${r.material_key}`} className={r.is_current ? "row-current" : ""}>
                    <td>
                      <strong>{r.process}</strong>
                      <div className="muted">{r.material}</div>
                      {r.design_changes.map((d, i) => (
                        <div key={i} className="design-change">
                          Design change: {d}
                        </div>
                      ))}
                      {r.extra_items.length > 0 && <div className="muted">Adds {r.extra_items.join(", ")}</div>}
                      {r.flags.map((f, i) => (
                        <SafetyBadge key={i} title={f.message} />
                      ))}
                      <details>
                        <summary>Trade-offs</summary>
                        <dl className="tech">
                          {Object.entries(r.tradeoffs).map(([k, v]) => (
                            <div key={k}>
                              <dt>{TRADEOFF_LABELS[k] ?? k}</dt>
                              <dd>{v}</dd>
                            </div>
                          ))}
                        </dl>
                      </details>
                    </td>
                    {vols.map((q) => (
                      <td key={q} className="nowrap-cell" title={`${gbp(r.costs[q].low)} – ${gbp(r.costs[q].high)}`}>
                        {gbp(r.costs[q].mid)}
                      </td>
                    ))}
                    <td className="nowrap-cell">{r.tooling.high === 0 ? "none" : `£${r.tooling.low.toLocaleString()}–£${r.tooling.high.toLocaleString()}`}</td>
                    <td>
                      {r.crossovers.slice(0, 3).map((x, i) => (
                        <div key={i}>{x.text}</div>
                      ))}
                    </td>
                    <td>
                      {r.is_current ? (
                        <span className="badge badge-status-accepted">current</span>
                      ) : (
                        <button onClick={() => select(p.part_id, r)}>Select</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ))}
    </section>
  );
}

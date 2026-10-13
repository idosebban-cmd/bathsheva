import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, errorText } from "../api";
import Md from "../components/InlineMarkdown";
import {
  allParts,
  extraPriceText,
  factoryTarget,
  gbp,
  matchesSearch,
  noPriceLabel,
  plainLines,
  priceLabel,
  QUANTITIES,
  sentence,
  type ConceptCost,
  type ConceptLine,
  type LibraryPart,
  type SavedConcept,
  type SeedConcept,
} from "../standardParts";
import { AvailabilityBadge, CostTiles, PriceCell, useStandardParts } from "./StandardPartsPage";

interface Draft {
  name: string;
  retail: string; // as typed, £ inc. VAT
  notes: string;
  basedOn: string | null;
  lines: ConceptLine[];
}

const BLANK: Draft = { name: "", retail: "", notes: "", basedOn: null, lines: [] };
const PICKER_LIMIT = 40;

function retailValue(text: string): number | null {
  const v = Number(text);
  return text.trim() && Number.isFinite(v) && v > 0 ? v : null;
}

/** /standard-parts/mine/new[?from=<concept key>] and /standard-parts/mine/:conceptId */
export default function ConceptBuilder() {
  const { library, parts } = useStandardParts();
  const { conceptId } = useParams();
  const [params] = useSearchParams();
  const from = params.get("from");
  const navigate = useNavigate();
  const savedId = conceptId && conceptId !== "new" ? Number(conceptId) : null;

  const [draft, setDraft] = useState<Draft | null>(null);
  const [dirty, setDirty] = useState(false);
  const [cost, setCost] = useState<ConceptCost | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [query, setQuery] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Load the saved concept, the product concept it starts from, or a blank one.
  useEffect(() => {
    let cancelled = false;
    setError("");
    setDraft(null);
    const done = (d: Draft, isDirty: boolean) => !cancelled && (setDraft(d), setDirty(isDirty));
    if (savedId !== null) {
      api.get<SavedConcept>(`/api/concepts/${savedId}`).then(
        (c) =>
          done(
            { name: c.name, retail: c.retail_price?.toString() ?? "", notes: c.notes, basedOn: c.based_on, lines: plainLines(c.lines) },
            false,
          ),
        (e) => !cancelled && setError(errorText(e)),
      );
    } else if (from) {
      api.get<SeedConcept[]>("/api/standard-parts/concepts").then(
        (all) => {
          const c = all.find((x) => x.key === from);
          if (!c) return !cancelled && setError(`No product concept called "${from}".`);
          done({ name: c.name, retail: c.retail_price?.toString() ?? "", notes: "", basedOn: c.key, lines: plainLines(c.lines) }, true);
        },
        (e) => !cancelled && setError(errorText(e)),
      );
    } else {
      done(BLANK, false);
    }
    return () => {
      cancelled = true;
    };
  }, [savedId, from]);

  // Running total: re-costed by the server on every change (the same calculation as the concept list).
  const linesKey = JSON.stringify(draft?.lines ?? []);
  const retail = retailValue(draft?.retail ?? "");
  useEffect(() => {
    if (!draft) return;
    let cancelled = false;
    const t = setTimeout(() => {
      api
        .post<ConceptCost>("/api/standard-parts/cost", { lines: draft.lines, retail_price: retail })
        .then((c) => !cancelled && setCost(c))
        .catch((e) => !cancelled && setError(errorText(e)));
    }, 120);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linesKey, retail, draft !== null]);

  // Warn before closing the tab with unsaved changes.
  useEffect(() => {
    if (!dirty) return;
    const h = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [dirty]);

  const picks = useMemo(() => allParts(library).filter((p) => query.trim() && matchesSearch(p, query)), [library, query]);

  if (error && !draft) return <p className="error">{error}</p>;
  if (!draft) return <p>Loading…</p>;

  const update = (patch: Partial<Draft>) => {
    setDraft({ ...draft, ...patch });
    setDirty(true);
  };
  const setLine = (i: number, patch: Partial<ConceptLine>) => update({ lines: draft.lines.map((l, j) => (j === i ? { ...l, ...patch } : l)) });
  const addPart = (p: LibraryPart) => update({ lines: [...draft.lines, { part_id: p.id, quantity: 1, note: "", option: 0 }] });
  const removeLine = (i: number) => update({ lines: draft.lines.filter((_, j) => j !== i) });
  const moveLine = (i: number, d: -1 | 1) => {
    const lines = [...draft.lines];
    [lines[i], lines[i + d]] = [lines[i + d], lines[i]];
    update({ lines });
  };

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError("");
    const body = { name: draft.name.trim(), retail_price: retail, based_on: draft.basedOn, notes: draft.notes, lines: draft.lines };
    try {
      const saved = savedId
        ? await api.put<SavedConcept>(`/api/concepts/${savedId}`, body)
        : await api.post<SavedConcept>("/api/concepts", body);
      setDirty(false);
      if (!savedId) navigate(`/standard-parts/mine/${saved.id}`, { replace: true });
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!savedId) return;
    try {
      await api.del(`/api/concepts/${savedId}`);
      navigate("/standard-parts/mine");
    } catch (e) {
      setError(errorText(e));
    }
  }

  // The server's figure once costed (the same rounding as the tiles); worked out here until then.
  const target = cost && cost.retail_price === retail ? cost.target : factoryTarget(retail, library.pricing);
  const pct = (share: number) => `${Math.round(share * 100)}%`;
  const costLine = (i: number) => (cost && cost.lines.length === draft.lines.length ? cost.lines[i] : null);

  return (
    <>
      <p className="small">
        <Link to="/standard-parts/mine">← My concepts</Link>
      </p>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>{savedId ? draft.name || "Untitled concept" : "New concept"}</h1>
        <div className="row">
          {dirty && <span className="badge badge-unverified">Unsaved changes</span>}
          <button className="primary" disabled={saving || !draft.name.trim() || (!dirty && savedId !== null)} onClick={save}>
            {saving ? "Saving…" : savedId ? "Save" : "Save concept"}
          </button>
          {savedId &&
            (confirmDelete ? (
              <>
                <span className="small">Delete this concept?</span>
                <button className="danger" onClick={remove}>
                  Delete
                </button>
                <button onClick={() => setConfirmDelete(false)}>Cancel</button>
              </>
            ) : (
              <button className="danger" onClick={() => setConfirmDelete(true)}>
                Delete
              </button>
            ))}
        </div>
      </div>
      {draft.basedOn && (
        <p className="small muted">
          Started from the product concept <Link to="/standard-parts/concepts">{sentence(draft.basedOn)}</Link>. Saving keeps your copy; the original in{" "}
          <code>product-ideas.md</code> doesn&apos;t change.
        </p>
      )}
      {error && <p className="error">{error}</p>}

      <section className="card sp-builder-head">
        <div className="row">
          <label className="field">
            <span>Name</span>
            <input value={draft.name} onChange={(e) => update({ name: e.target.value })} placeholder="e.g. Brass column lamp" />
          </label>
          <label className="field">
            <span>Retail price (£ inc. VAT)</span>
            <input type="number" min={0} step="any" value={draft.retail} onChange={(e) => update({ retail: e.target.value })} placeholder="e.g. 195" />
          </label>
          <div className="field">
            <span>Factory-cost target</span>
            <span className="tile-big">{target !== null ? gbp(target) : "—"}</span>
            <span className="small muted">
              {retail !== null
                ? `${gbp(retail)} ÷ ${1 + library.pricing.vat_rate} VAT × ${library.pricing.dtc_factory_share} (DTC factory share)`
                : "Enter a retail price"}
            </span>
          </div>
        </div>
        {cost && <CostTiles cost={cost} />}
        {cost && cost.target !== null && (
          <p className="small muted">
            Parts only. Below {pct(library.room_share)} of the target leaves room for labour, finishing and freight; up to 100% is tight;
            above is over.
          </p>
        )}
        {cost && cost.unpriced.length > 0 && (
          <p className="notice small">
            {cost.unpriced.length} part{cost.unpriced.length === 1 ? " has" : "s have"} no listed price and count as £0, so the total is a
            floor.
          </p>
        )}
        {cost && cost.unknown.length > 0 && <p className="error small">Not in the library any more: {cost.unknown.join(", ")}</p>}
        <label className="field">
          <span>Notes</span>
          <textarea rows={2} value={draft.notes} onChange={(e) => update({ notes: e.target.value })} placeholder="Custom work, risks, open questions" />
        </label>
      </section>

      <section className="card">
        <h2>Parts</h2>
        <p className="small muted">
          The quantity is in the unit the price is for: a price &quot;per 2.5 m&quot; with quantity 0.12 is 300 mm; a sheet price with 0.16 is
          16% of the sheet. Price breaks apply when 100 or 500 products need enough to reach them.
        </p>
        {draft.lines.length === 0 ? (
          <p className="muted">No parts yet. Search the library below to add some.</p>
        ) : (
          <div className="table-wrap">
            <table className="sp-lines">
              <thead>
                <tr>
                  <th>Part</th>
                  <th>Price</th>
                  <th>Qty</th>
                  <th>Note</th>
                  {QUANTITIES.map((q) => (
                    <th key={q} className="num">
                      @{q}
                    </th>
                  ))}
                  <th />
                </tr>
              </thead>
              <tbody>
                {draft.lines.map((l, i) => {
                  const p = parts.get(l.part_id);
                  const c = costLine(i);
                  return (
                    <tr key={i}>
                      <td>
                        {p ? (
                          <>
                            <strong>{p.name}</strong> <AvailabilityBadge part={p} />
                            <div className="small muted">
                              {p.supplier}
                              {p.links[0] && (
                                <>
                                  {" · "}
                                  <a href={p.links[0].url} target="_blank" rel="noreferrer">
                                    link
                                  </a>
                                </>
                              )}
                            </div>
                          </>
                        ) : (
                          <span className="error">Not in the library: {l.part_id}</span>
                        )}
                      </td>
                      <td>
                        {p && p.options.length > 1 ? (
                          <select value={l.option} onChange={(e) => setLine(i, { option: Number(e.target.value) })}>
                            {p.options.map((o, k) => (
                              <option key={k} value={k}>
                                {priceLabel(o)}
                                {o.label ? ` (${o.label})` : ""}
                              </option>
                            ))}
                          </select>
                        ) : p && p.options.length === 1 ? (
                          <span>{priceLabel(p.options[0])}</span>
                        ) : (
                          p && <span className="badge badge-unverified">{noPriceLabel(p)}</span>
                        )}
                        {p && extraPriceText(p) && (
                          <div className="small muted sp-price-text">
                            <Md text={p.price_text} />
                          </div>
                        )}
                      </td>
                      <td>
                        <input
                          className="sp-qty"
                          type="number"
                          min={0}
                          step="any"
                          value={l.quantity}
                          onChange={(e) => setLine(i, { quantity: Math.max(0, Number(e.target.value) || 0) })}
                        />
                      </td>
                      <td>
                        <input className="sp-note-input" value={l.note} onChange={(e) => setLine(i, { note: e.target.value })} placeholder="What it's for" />
                      </td>
                      {QUANTITIES.map((q) => (
                        <td key={q} className="num nowrap-cell">
                          {c ? gbp(c[`cost_${q}`]) : "…"}
                          {c?.[`break_${q}`] && (
                            <span className="badge" title="A listed price break applies at this quantity">
                              break
                            </span>
                          )}
                        </td>
                      ))}
                      <td className="nowrap-cell">
                        <button className="link" disabled={i === 0} onClick={() => moveLine(i, -1)} title="Move up">
                          ↑
                        </button>
                        <button className="link" disabled={i === draft.lines.length - 1} onClick={() => moveLine(i, 1)} title="Move down">
                          ↓
                        </button>
                        <button className="link" onClick={() => removeLine(i)}>
                          remove
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {cost && (
                  <tr className="sp-total">
                    <td colSpan={4}>Parts total</td>
                    {QUANTITIES.map((q) => (
                      <td key={q} className="num">
                        {gbp(cost[`total_${q}`])}
                        {cost[`share_${q}`] !== null && <div className="small muted">{pct(cost[`share_${q}`] as number)} of target</div>}
                      </td>
                    ))}
                    <td />
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Add parts from the library</h2>
        <input
          type="search"
          className="sp-search"
          placeholder="Search by part, material, supplier or category (e.g. brass tube, opal globe, battery)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {query.trim() && (
          <>
            <p className="small muted">
              {picks.length} match{picks.length === 1 ? "" : "es"}
              {picks.length > PICKER_LIMIT && `; showing the first ${PICKER_LIMIT}`}
            </p>
            <div className="table-wrap">
              <table>
                <tbody>
                  {picks.slice(0, PICKER_LIMIT).map((p) => (
                    <tr key={p.id}>
                      <td>
                        <strong>{p.name}</strong> <AvailabilityBadge part={p} />
                        <div className="small muted">
                          {p.subcategory} · {p.material} · {p.sizes}
                        </div>
                      </td>
                      <td>{p.supplier}</td>
                      <td>
                        <PriceCell part={p} />
                      </td>
                      <td>
                        <button onClick={() => addPart(p)}>Add</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </>
  );
}

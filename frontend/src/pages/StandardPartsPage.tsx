import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useOutletContext } from "react-router-dom";
import { api, errorText } from "../api";
import { ukDateTime } from "../format";
import Md from "../components/InlineMarkdown";
import {
  extraPriceText,
  gbp,
  matchesSearch,
  noPriceLabel,
  priceLabel,
  QUANTITIES,
  sentence,
  VERDICT_LABEL,
  VERDICT_TILE,
  type ConceptCost,
  type Library,
  type LibraryPart,
  type SavedConcept,
  type SeedConcept,
} from "../standardParts";

export interface StandardPartsContext {
  library: Library;
  parts: Map<string, LibraryPart>;
}

export const useStandardParts = () => useOutletContext<StandardPartsContext>();

/** Layout for /standard-parts: loads the library once and shows the sub-tabs. */
export default function StandardPartsPage() {
  const [library, setLibrary] = useState<Library | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.get<Library>("/api/standard-parts").then(setLibrary, (e) => setError(errorText(e)));
  }, []);
  const parts = useMemo(
    () => new Map((library?.sections ?? []).flatMap((s) => s.subsections.flatMap((sub) => sub.parts.map((p) => [p.id, p] as const)))),
    [library],
  );
  return (
    <div>
      <nav className="tabs">
        <NavLink to="library">Parts library</NavLink>
        <NavLink to="concepts">Product concepts</NavLink>
        <NavLink to="mine">My concepts</NavLink>
      </nav>
      <main className="page standard-parts">
        {error ? <p className="error">{error}</p> : !library ? <p>Loading the parts library…</p> : <Outlet context={{ library, parts }} />}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared bits
// ---------------------------------------------------------------------------

export function PriceCell({ part }: { part: LibraryPart }) {
  const none = noPriceLabel(part);
  return (
    <div>
      {none ? (
        <span className={`badge ${part.price_status === "quote" ? "badge-assumption" : "badge-unverified"}`}>{none}</span>
      ) : (
        <strong>{priceLabel(part.options[0])}</strong>
      )}{" "}
      {part.price_from && <span className="badge" title="The figure is the cheapest of a range or a 'from' price">from</span>}{" "}
      {part.price_uncertain && <span className="badge badge-unverified" title="The listing says to confirm this price">confirm</span>}
      {extraPriceText(part) && (
        <div className="small muted">
          <Md text={part.price_text} />
        </div>
      )}
    </div>
  );
}

export function AvailabilityBadge({ part }: { part: LibraryPart }) {
  if (!part.availability) return null;
  return (
    <span className="badge badge-safety" title={`The listing says: ${part.availability}`}>
      {part.availability.includes("discontinued") || part.availability.includes("no longer") ? "Discontinued?" : "Out of stock?"}
    </span>
  );
}

export function CostTiles({ cost, showTarget = true }: { cost: ConceptCost; showTarget?: boolean }) {
  return (
    <div className="summary-tiles">
      {QUANTITIES.map((q) => {
        const verdict = cost[`verdict_${q}`];
        const share = cost[`share_${q}`];
        return (
          <div key={q} className={`tile ${verdict ? VERDICT_TILE[verdict] : ""}`}>
            <b>{gbp(cost[`total_${q}`])}</b> parts @{q}
            {showTarget && share !== null && verdict && (
              <span>
                {" "}
                · {Math.round(share * 100)}% of target · {VERDICT_LABEL[verdict]}
              </span>
            )}
          </div>
        );
      })}
      {showTarget && cost.target !== null && (
        <div className="tile">
          <b>{gbp(cost.target)}</b> factory-cost target
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Parts library
// ---------------------------------------------------------------------------

export function LibraryView() {
  const { library } = useStandardParts();
  const [query, setQuery] = useState("");
  const [pricedOnly, setPricedOnly] = useState(false);
  const total = library.sections.reduce((n, s) => n + s.subsections.reduce((m, sub) => m + sub.parts.length, 0), 0);
  const show = (p: LibraryPart) => matchesSearch(p, query) && (!pricedOnly || p.price_status === "listed");
  const shown = library.sections.reduce((n, s) => n + s.subsections.reduce((m, sub) => m + sub.parts.filter(show).length, 0), 0);

  return (
    <>
      <h1>Standard parts library</h1>
      <p className="muted">
        Off-the-shelf parts from UK and EU suppliers in small quantities, read from <code>standard-parts/library.md</code>. Prices are
        search snapshots: none are verified, so confirm on the supplier&apos;s page before relying on one.
      </p>
      {library.about.map((a) => (
        <details key={a.title} className="card sp-about">
          <summary>{a.title}</summary>
          {a.lines.map((l, i) => (
            <p key={i} className="small">
              <Md text={l.replace(/^\s*-\s+/, "• ")} />
            </p>
          ))}
        </details>
      ))}
      <div className="row sp-filter">
        <input type="search" placeholder="Search parts, materials, suppliers…" value={query} onChange={(e) => setQuery(e.target.value)} />
        <label className="checkbox">
          <input type="checkbox" checked={pricedOnly} onChange={(e) => setPricedOnly(e.target.checked)} /> Listed price only
        </label>
        <span className="muted small">
          {shown} of {total} parts
        </span>
      </div>
      {library.sections.map((s) => {
        const subs = s.subsections.map((sub) => ({ ...sub, parts: sub.parts.filter(show) })).filter((sub) => sub.parts.length || !query);
        if (!subs.some((sub) => sub.parts.length)) return null;
        return (
          <section key={s.number} className="card sp-section">
            <h2>
              {s.number}. {s.title}
            </h2>
            {subs.map((sub) => (
              <div key={sub.number} className="sp-subsection">
                <h3>
                  {sub.number} {sub.title}
                </h3>
                {sub.parts.length > 0 && (
                  <div className="table-wrap">
                    <table className="sp-table">
                      <thead>
                        <tr>
                          <th>Part</th>
                          <th>Material</th>
                          <th>Sizes</th>
                          <th>Supplier</th>
                          <th>Unit price</th>
                          <th>MOQ</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sub.parts.map((p) => (
                          <tr key={p.id}>
                            <td>
                              <strong>{p.name}</strong> <AvailabilityBadge part={p} />
                              {p.note && (
                                <div className="small muted">
                                  <Md text={p.note} />
                                </div>
                              )}
                            </td>
                            <td>{p.material}</td>
                            <td>{p.sizes}</td>
                            <td>
                              {p.supplier}
                              <div className="small">
                                {p.links.map((l, i) => (
                                  <span key={l.url}>
                                    {i > 0 && " · "}
                                    <a href={l.url} target="_blank" rel="noreferrer">
                                      {l.label}
                                    </a>
                                  </span>
                                ))}
                              </div>
                            </td>
                            <td>
                              <PriceCell part={p} />
                              {p.breaks_text && p.breaks_text !== "—" && (
                                <div className="small">
                                  <span className="muted">Breaks:</span> <Md text={p.breaks_text} />
                                </div>
                              )}
                            </td>
                            <td>{p.moq}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {!query &&
                  sub.notes.map((n, i) => (
                    <p key={i} className="small sp-note">
                      <Md text={n} />
                    </p>
                  ))}
              </div>
            ))}
          </section>
        );
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// The 15 concepts from product-ideas.md
// ---------------------------------------------------------------------------

export function ConceptsView() {
  const { parts } = useStandardParts();
  const [concepts, setConcepts] = useState<SeedConcept[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.get<SeedConcept[]>("/api/standard-parts/concepts").then(setConcepts, (e) => setError(errorText(e)));
  }, []);
  if (error) return <p className="error">{error}</p>;
  if (!concepts) return <p>Loading concepts…</p>;

  return (
    <>
      <h1>Product concepts</h1>
      <p className="muted">
        The {concepts.length} concepts in <code>standard-parts/product-ideas.md</code>. Costs are parts only, worked out from the library
        at 100 and 500 units, against the direct-to-consumer factory-cost target (a third of the ex-VAT retail price). Labour, finishing,
        certification and packaging are not included. Open one in the builder to change its parts; the original stays as it is.
      </p>
      {concepts.map((c) => (
        <section key={c.key} className="card sp-concept">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h2>
              {c.number}. {c.name} <span className="muted">— {c.subtitle}</span>
            </h2>
            <Link className="button primary" to={`/standard-parts/mine/new?from=${encodeURIComponent(c.key)}`}>
              Open in builder
            </Link>
          </div>
          <p className="small muted">
            {c.group} · retail {c.retail_price ? gbp(c.retail_price) : "not set"}
          </p>
          <CostTiles cost={c.cost} />
          <p>
            <Md text={c.description} />
          </p>
          <div className="sp-concept-grid">
            <div>
              <h3>Library parts</h3>
              <ul className="small">
                {c.library_parts.map((p, i) => (
                  <li key={i}>
                    <Md text={p} />
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Custom work</h3>
              <p className="small">
                <Md text={sentence(c.custom_work)} />
              </p>
              {c.not_in_library && (
                <>
                  <h3>Not in library</h3>
                  <p className="small">
                    <Md text={sentence(c.not_in_library)} />
                  </p>
                </>
              )}
              <h3>Main risk</h3>
              <p className="small">
                <Md text={sentence(c.main_risk)} />
              </p>
            </div>
          </div>
          <details>
            <summary>Costed parts list</summary>
            <CostTable cost={c.cost} parts={parts} />
          </details>
        </section>
      ))}
    </>
  );
}

function CostTable({ cost, parts }: { cost: ConceptCost; parts: Map<string, LibraryPart> }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Part</th>
            <th>Qty</th>
            <th>For</th>
            {QUANTITIES.map((q) => (
              <th key={q} className="num">
                @{q}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cost.lines.map((l, i) => {
            const p = parts.get(l.part_id);
            return (
              <tr key={i}>
                <td>
                  {p ? p.name : <span className="error">Not in the library: {l.part_id}</span>}
                  {p && <div className="small muted">{p.supplier}</div>}
                </td>
                <td className="num">{+l.quantity.toFixed(5)}</td>
                <td className="small">{l.note}</td>
                {QUANTITIES.map((q) => (
                  <td key={q} className="num">
                    {gbp(l[`cost_${q}`])}
                    {l[`break_${q}`] && <span className="badge" title="A listed price break applies">break</span>}
                  </td>
                ))}
              </tr>
            );
          })}
          <tr className="sp-total">
            <td colSpan={3}>Parts total</td>
            {QUANTITIES.map((q) => (
              <td key={q} className="num">
                {gbp(cost[`total_${q}`])}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// My concepts
// ---------------------------------------------------------------------------

export function MyConceptsView() {
  const [concepts, setConcepts] = useState<SavedConcept[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.get<SavedConcept[]>("/api/concepts").then(setConcepts, (e) => setError(errorText(e)));
  }, []);
  if (error) return <p className="error">{error}</p>;
  if (!concepts) return <p>Loading…</p>;
  return (
    <>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>My concepts</h1>
        <Link className="button primary" to="/standard-parts/mine/new">
          + New concept
        </Link>
      </div>
      <p className="muted">
        Concepts you have built from library parts, saved in the workbench database. Start from scratch, or open one of the{" "}
        <Link to="/standard-parts/concepts">product concepts</Link> as a starting point.
      </p>
      {concepts.length === 0 ? (
        <p className="muted">No saved concepts yet.</p>
      ) : (
        <ul className="project-list">
          {concepts.map((c) => (
            <li key={c.id} className="card">
              <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
                <Link to={`/standard-parts/mine/${c.id}`} className="project-name">
                  {c.name}
                </Link>
                <span className="small muted">
                  {c.lines.length} part{c.lines.length === 1 ? "" : "s"} · retail {c.retail_price ? gbp(c.retail_price) : "not set"}
                  {c.based_on && ` · from ${sentence(c.based_on)}`} · updated {ukDateTime(c.updated_at)}
                </span>
              </div>
              <CostTiles cost={c.cost} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

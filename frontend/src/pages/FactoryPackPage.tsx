import { useEffect, useState } from "react";
import { api, errorText, type FactoryPackSummary } from "../api";
import { SafetyBadge, UnverifiedBadge } from "../components/Badges";
import { useProject } from "../components/useProject";

export default function FactoryPackPage() {
  const { project } = useProject();
  const [pack, setPack] = useState<FactoryPackSummary | null>(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [showRfq, setShowRfq] = useState(false);
  const base = `/api/projects/${project.id}`;

  async function load() {
    try {
      setError("");
      setPack(await api.get<FactoryPackSummary>(`${base}/factory-pack`));
    } catch (e) {
      setError(errorText(e));
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  if (!pack) return <p>{error || "Loading…"}</p>;

  return (
    <div className="stack">
      <section className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2>Factory Pack: request for quotation</h2>
          <div className="row">
            <button onClick={load}>Refresh</button>
            {pack.ready ? (
              <a href={`${base}/factory-pack.zip`} download>
                <button className="primary">Download RFQ pack (.zip)</button>
              </a>
            ) : (
              <button disabled title="Generate CAD first">Download RFQ pack (.zip)</button>
            )}
          </div>
        </div>
        <p className="small muted">
          {pack.ready ? `Uses CAD v${pack.cad_version}.` : "Generate CAD on the CAD tab first: the pack includes the STEP files."} The zip holds a 2D
          drawing (PDF and SVG) and a STEP file per made-to-drawing part, the full assembly STEP, the RFQ document (PDF and Markdown) and the BOM
          CSV. Quantity tiers: {pack.quantity_tiers.map((q) => q.toLocaleString()).join(" / ")}.
        </p>
        <div className="row">
          <a href={`${base}/rfq.pdf`} target="_blank" rel="noreferrer">
            <button>RFQ (PDF)</button>
          </a>
          <a href={`${base}/rfq.md`} download>
            <button>RFQ (Markdown)</button>
          </a>
          <button onClick={() => setShowRfq(!showRfq)}>{showRfq ? "Hide" : "Show"} RFQ text</button>
        </div>
        {pack.notes.map((n) => (
          <p key={n} className="notice small">
            {n}
          </p>
        ))}
      </section>

      <section className="card">
        <h2>Drawings</h2>
        <table>
          <thead>
            <tr>
              <th>Part no.</th>
              <th>Part</th>
              <th>Qty</th>
              <th>Material / process</th>
              <th>Finish</th>
              <th>Checks</th>
              <th>Drawing</th>
            </tr>
          </thead>
          <tbody>
            {pack.parts.map((p) => (
              <tr key={p.cad_key}>
                <td>{p.part_no}</td>
                <td>{p.name}</td>
                <td>{p.quantity}</td>
                <td>
                  {p.material || "TBD"}
                  <div className="small muted">{p.process || "TBD"}</div>
                </td>
                <td>{p.finish}</td>
                <td className="small">
                  {p.unverified.map((u) => (
                    <div key={u}>
                      <UnverifiedBadge title={u} /> {u}
                    </div>
                  ))}
                  {p.safety.map((s) => (
                    <div key={s}>
                      <SafetyBadge title={s} /> {s}
                    </div>
                  ))}
                </td>
                <td>
                  <div className="row">
                    <button onClick={() => setPreview(preview === p.cad_key ? null : p.cad_key)}>
                      {preview === p.cad_key ? "Hide" : "Preview"}
                    </button>
                    <a href={`${base}/drawings/${p.cad_key}.pdf`} target="_blank" rel="noreferrer">
                      PDF
                    </a>
                    <a href={`${base}/drawings/${p.cad_key}.svg`} target="_blank" rel="noreferrer">
                      SVG
                    </a>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {preview && (
          <div className="drawing-preview">
            <img src={`${base}/drawings/${preview}.svg`} alt={`Drawing of ${preview}`} style={{ width: "100%", background: "#fff" }} />
          </div>
        )}
      </section>

      <section className="card">
        <h2>Before you send it</h2>
        {pack.mass && (
          <p>
            Estimated lamp mass <b>{pack.mass.total_kg.toFixed(2)} kg</b>
            {pack.mass.target_kg ? ` vs target ${pack.mass.target_kg} kg (${pack.mass.status})` : ""}. <span className="small muted">{pack.mass.note}</span>
          </p>
        )}
        <h3>Compliance</h3>
        <ul>
          {pack.compliance.map((c) => (
            <li key={c}>
              <SafetyBadge title="Compliance verification needed" /> {c}
            </li>
          ))}
        </ul>
        <h3>Safety items ({pack.safety.length})</h3>
        <ul className="small">
          {pack.safety.map((s) => (
            <li key={s}>
              <SafetyBadge title="Verify with human / manufacturer" /> {s}
            </li>
          ))}
        </ul>
        <h3>Unverified values ({pack.unverified.length})</h3>
        <ul className="small">
          {pack.unverified.map((u) => (
            <li key={u}>
              <UnverifiedBadge title="Unverified" /> {u}
            </li>
          ))}
        </ul>
        <h3>Bought-in components listed in the RFQ</h3>
        <ul className="small">
          {pack.bought_in.map((b) => (
            <li key={b.name}>
              {b.quantity} × {b.name} {b.electronics && <SafetyBadge title="Certified for UK/EU sale: verify certificates" />}
            </li>
          ))}
        </ul>
      </section>

      {showRfq && (
        <section className="card">
          <h2>RFQ text</h2>
          <pre className="rfq-text">{pack.rfq_markdown}</pre>
        </section>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { api, errorText, type FactoryPackSummary } from "../api";
import { SafetyBadge, UnverifiedBadge } from "../components/Badges";
import { useProject } from "../components/useProject";

export default function FactoryPackPage() {
  const { project } = useProject();
  const [pack, setPack] = useState<FactoryPackSummary | null>(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [showRfq, setShowRfq] = useState<"" | "mechanical" | "electronics">("");
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
          {pack.ready ? `Uses CAD v${pack.cad_version}.` : "Generate CAD on the CAD tab first: the pack includes the STEP files."} The zip has
          two folders. <b>mechanical/</b> (for metalwork, glass and finishing suppliers) holds a 2D drawing (PDF and SVG) and a STEP file per
          made-to-drawing part, the assembly STEP, the RFQ and the BOM. <b>electronics/</b> holds a separate RFQ for the battery pack, control
          board and LEDs. Quantity tiers: {pack.quantity_tiers.map((q) => q.toLocaleString()).join(" / ")}.
        </p>
        <div className="row">
          <a href={`${base}/rfq.pdf`} target="_blank" rel="noreferrer">
            <button>Mechanical RFQ (PDF)</button>
          </a>
          <a href={`${base}/rfq-electronics.pdf`} target="_blank" rel="noreferrer">
            <button>Electronics RFQ (PDF)</button>
          </a>
          <button onClick={() => setShowRfq(showRfq === "mechanical" ? "" : "mechanical")}>
            {showRfq === "mechanical" ? "Hide" : "Show"} mechanical RFQ text
          </button>
          <button onClick={() => setShowRfq(showRfq === "electronics" ? "" : "electronics")}>
            {showRfq === "electronics" ? "Hide" : "Show"} electronics RFQ text
          </button>
        </div>
        {pack.missing_contact.length > 0 && (
          <p className="notice small">
            <SafetyBadge title="Fill in before sending" /> Contact details missing: {pack.missing_contact.join(", ")}. The RFQs show
            placeholders for them until you fill them in below.
          </p>
        )}
        {pack.notes.map((n) => (
          <p key={n} className="notice small">
            {n}
          </p>
        ))}
      </section>

      <ContactCard pack={pack} base={base} onSaved={load} />

      {pack.consistency.length > 0 && (
        <section className="card">
          <h2>Consistency with the latest CAD</h2>
          <table>
            <tbody>
              {pack.consistency.map((c) => (
                <tr key={c.check}>
                  <td>
                    <span className={`status status-${c.ok ? "pass" : c.level === "warn" ? "close" : "fail"}`}>
                      {c.ok ? "✓ OK" : c.level === "warn" ? "! Warning" : "✗ Fix"}
                    </span>
                  </td>
                  <td>{c.check}</td>
                  <td className="small muted">{c.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="card">
        <h2>
          Supplier questions ({pack.open_questions.filter((q) => q.status === "open").length} open of {pack.open_questions.length})
        </h2>
        <p className="small muted">Answers go into the RFQs. This list itself is never sent.</p>
        {pack.placeholders.length > 0 && (
          <p className="notice small">
            Fill in before sending (in both RFQs): {pack.placeholders.join(", ")}
          </p>
        )}
        <table>
          <thead>
            <tr>
              <th>Topic</th>
              <th>Question</th>
              <th>Answer in the RFQ</th>
            </tr>
          </thead>
          <tbody>
            {pack.open_questions.map((q) => (
              <tr key={q.id}>
                <td>{q.topic}</td>
                <td>
                  {q.question}
                  <div className="small muted">{q.why}</div>
                </td>
                <td className="small">
                  {q.status === "resolved" ? (
                    <><span className="status status-pass">✓</span> {q.answer}</>
                  ) : (
                    <><span className="status status-close">Open</span> Proposed: {q.proposed}</>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
        <h3>Brass parts quoted two ways (preferred and near-net)</h3>
        <ul className="small">
          {pack.brass_parts.map((b) => (
            <li key={b.part_no}>
              {b.part_no} {b.name}: {b.near_net}
            </li>
          ))}
        </ul>
        <h3>Bought-in components (electronics go to the electronics RFQ)</h3>
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
          <h2>{showRfq === "mechanical" ? "Mechanical" : "Electronics"} RFQ text</h2>
          <pre className="rfq-text">{showRfq === "mechanical" ? pack.rfq_markdown : pack.electronics_rfq_markdown}</pre>
        </section>
      )}
    </div>
  );
}

function ContactCard({ pack, base, onSaved }: { pack: FactoryPackSummary; base: string; onSaved: () => Promise<void> }) {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const dirty = Object.keys(draft).length > 0;

  async function save() {
    setStatus("Saving…");
    try {
      await api.put(`${base}/factory-pack/contact`, draft);
      setDraft({});
      setStatus("Saved");
      await onSaved();
    } catch (e) {
      setStatus(errorText(e));
    }
  }

  return (
    <section className="card">
      <h2>Your details for the RFQs</h2>
      <p className="small muted">
        Saved on this project and filled into both RFQs (mechanical and electronics) when the pack is built. Blank fields stay as
        placeholders.
      </p>
      <div className="grid">
        {pack.contact_fields.map((f) => {
          const value = draft[f.key] ?? pack.contact[f.key] ?? "";
          const multiline = f.key.endsWith("address");
          return (
            <label key={f.key} className="field">
              <span>
                {f.label} {!value.trim() && <span className="badge badge-unverified">empty</span>}
              </span>
              {multiline ? (
                <textarea rows={2} value={value} placeholder={f.placeholder}
                  onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })} />
              ) : (
                <input value={value} placeholder={f.placeholder} type={f.key === "email" ? "email" : "text"}
                  onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value })} />
              )}
            </label>
          );
        })}
      </div>
      <div className="row">
        <button className="primary" disabled={!dirty} onClick={save}>Save details</button>
        <span className="muted small">{status}</span>
      </div>
    </section>
  );
}

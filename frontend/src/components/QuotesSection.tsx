import { useCallback, useEffect, useState } from "react";
import { api, errorText, fileUrl, type Part, type PartQuotes, type RevisionSummary } from "../api";

const STATUS_LABEL: Record<string, string> = {
  below: "Below estimate",
  within: "Within estimate",
  above: "Above estimate",
  currency_mismatch: "Different currency",
  no_estimate: "No estimate",
};

const today = () => new Date().toISOString().slice(0, 10);

/** Real supplier quotes for one part, compared against the workbench estimate. Review only. */
export default function QuotesSection({ part }: { part: Part }) {
  const [data, setData] = useState<PartQuotes | null>(null);
  const [revisions, setRevisions] = useState<RevisionSummary[]>([]);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setData(await api.get<PartQuotes>(`/api/projects/${part.project_id}/parts/${part.id}/quotes`));
    } catch (e) {
      setError(errorText(e));
    }
  }, [part.project_id, part.id]);

  useEffect(() => {
    load();
    api.get<RevisionSummary[]>(`/api/projects/${part.project_id}/revisions`).then(setRevisions, () => undefined);
  }, [load, part.project_id, part.cost_low, part.cost_high]);

  async function submit(form: HTMLFormElement) {
    setError("");
    const fd = new FormData(form);
    for (const key of ["lead_time_days", "revision_id"]) if (fd.get(key) === "") fd.delete(key);
    const file = fd.get("attachment");
    if (file instanceof File && !file.name) fd.delete("attachment");
    try {
      await api.post(`/api/projects/${part.project_id}/parts/${part.id}/quotes`, fd);
      setAdding(false);
      await load();
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function remove(id: number, source: string) {
    if (!confirm(`Delete the ${source} quote?`)) return;
    await api.del(`/api/projects/${part.project_id}/quotes/${id}`);
    await load();
  }

  if (!data) return <section className="card">{error || "Loading quotes…"}</section>;
  const est = data.estimate;
  const money = (v: number, c: string) => `${c} ${v.toFixed(2)}`;

  return (
    <section className="card quotes">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>External quotes: {part.name}</h2>
        {!adding && <button onClick={() => setAdding(true)}>+ Add quote</button>}
      </div>
      <p className="small muted">{data.note}</p>
      <div className="estimate-box">
        <strong>Workbench estimate (unit):</strong>{" "}
        {est ? (
          <>
            {money(est.low, est.currency)} – {money(est.high, est.currency)} <span className="muted small">· {est.basis}</span>
          </>
        ) : (
          <span className="muted">not set. Add a cost estimate to this part to compare.</span>
        )}
      </div>

      {adding && (
        <form
          className="quote-form"
          onSubmit={(e) => {
            e.preventDefault();
            submit(e.currentTarget);
          }}
        >
          <div className="grid">
            <label>
              Source*
              <input name="source" required placeholder="e.g. Xometry" />
            </label>
            <label>
              Quote date*
              <input name="quote_date" type="date" required defaultValue={today()} />
            </label>
            <label>
              Quantity*
              <input name="quantity" type="number" min={1} required defaultValue={part.quantity} />
            </label>
            <label>
              Unit price*
              <input name="unit_price" type="number" min={0} step="0.01" required />
            </label>
            <label>
              Currency
              <input name="currency" defaultValue="GBP" maxLength={3} />
            </label>
            <label>
              Lead time (days)
              <input name="lead_time_days" type="number" min={0} />
            </label>
            <label>
              Process quoted
              <input name="process" defaultValue={part.process} />
            </label>
            <label>
              Material quoted
              <input name="material" defaultValue={part.material} />
            </label>
            <label>
              Finish quoted
              <input name="finish" defaultValue={part.finish} />
            </label>
            <label>
              Design revision
              <select name="revision_id" defaultValue={revisions[0]?.id ?? ""}>
                <option value="">(none)</option>
                {revisions.map((r) => (
                  <option key={r.id} value={r.id}>
                    Rev {r.number}
                    {r.note ? `: ${r.note}` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Attachment (PDF, image, spreadsheet…)
              <input name="attachment" type="file" />
            </label>
          </div>
          <label className="field">
            DFM notes / supplier feedback
            <textarea name="dfm_notes" rows={3} />
          </label>
          <div className="row">
            <button className="primary" type="submit">
              Save quote
            </button>
            <button type="button" onClick={() => setAdding(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
      {error && <p className="error">{error}</p>}

      {data.quotes.length === 0 ? (
        <p className="muted small">No quotes recorded for this part.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Qty</th>
                <th>Unit price</th>
                <th>vs estimate</th>
                <th>Quoted as</th>
                <th>Lead time</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.quotes.map((q) => (
                <tr key={q.id}>
                  <td>
                    <strong>{q.source}</strong>
                    <div className="muted small">
                      {q.quote_date}
                      {q.revision_number && ` · Rev ${q.revision_number}`}
                    </div>
                    {q.attachment_path && (
                      <a className="small" href={fileUrl(q.attachment_path)} target="_blank" rel="noreferrer">
                        {q.attachment_filename}
                      </a>
                    )}
                  </td>
                  <td>{q.quantity}</td>
                  <td>
                    {money(q.unit_price, q.currency)}
                    <div className="muted small">total {money(q.total_price, q.currency)}</div>
                  </td>
                  <td>
                    <span className={`cmp cmp-${q.comparison.status}`}>{STATUS_LABEL[q.comparison.status]}</span>
                    {q.comparison.diff_pct !== null && q.comparison.status !== "within" && (
                      <strong className={`cmp-pct cmp-${q.comparison.status}`}> {q.comparison.diff_pct > 0 ? "+" : ""}{q.comparison.diff_pct}%</strong>
                    )}
                    <div className="muted small">{q.comparison.text}</div>
                  </td>
                  <td className="small">
                    {[q.process, q.material, q.finish].filter(Boolean).join(" · ") || <span className="muted">—</span>}
                    {q.dfm_notes && <div className="dfm-note">DFM: {q.dfm_notes}</div>}
                  </td>
                  <td>{q.lead_time_days !== null ? `${q.lead_time_days} days` : <span className="muted">—</span>}</td>
                  <td>
                    <button className="link danger" onClick={() => remove(q.id, q.source)}>
                      delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

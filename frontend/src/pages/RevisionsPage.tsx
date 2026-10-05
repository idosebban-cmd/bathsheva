import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText, type Revision, type RevisionSummary } from "../api";
import { useProject } from "../components/useProject";

export default function RevisionsPage() {
  const { project } = useProject();
  const [revisions, setRevisions] = useState<RevisionSummary[]>([]);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");

  const load = useCallback(async () => {
    setRevisions(await api.get<RevisionSummary[]>(`/api/projects/${project.id}/revisions`));
  }, [project.id]);
  useEffect(() => {
    load();
  }, [load]);

  async function save() {
    setStatus("Saving…");
    try {
      const r = await api.post<Revision>(`/api/projects/${project.id}/revisions`, { note });
      setNote("");
      setStatus(`Saved revision ${r.number}`);
      await load();
    } catch (e) {
      setStatus(errorText(e));
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>Save a revision</h2>
        <p className="small muted">
          A revision is an immutable snapshot of the requirements, CAD parameters and latest CAD files, parts, decisions and
          recommendations. Generate CAD first if you want the snapshot to include your latest parameter changes.
        </p>
        <div className="row">
          <input style={{ flex: 1 }} placeholder="What changed? (e.g. taller body for retail sample)" value={note} onChange={(e) => setNote(e.target.value)} />
          <button className="primary" onClick={save}>
            Save revision
          </button>
          <span className="muted small">{status}</span>
        </div>
      </section>
      <section className="card">
        <h2>History</h2>
        {revisions.length === 0 ? (
          <p className="muted">No revisions yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Revision</th>
                <th>Note</th>
                <th>Saved</th>
              </tr>
            </thead>
            <tbody>
              {revisions.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`${r.number}`}>Rev {r.number}</Link>
                  </td>
                  <td>{r.note || <span className="muted">(no note)</span>}</td>
                  <td>{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

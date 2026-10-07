import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorText, type ProductTemplate, type Project, type ProjectSummary } from "../api";
import { ukDateTime } from "../format";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [templates, setTemplates] = useState<ProductTemplate[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();

  function load() {
    api.get<ProjectSummary[]>("/api/projects").then(setProjects, (e) => setError(errorText(e)));
  }
  useEffect(load, []);
  useEffect(() => {
    api.get<ProductTemplate[]>("/api/templates").then(setTemplates, (e) => setError(errorText(e)));
  }, []);

  async function remove(p: ProjectSummary) {
    setDeleting(true);
    setError("");
    try {
      await api.del(`/api/projects/${p.id}`);
      setConfirming(null);
      load();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setDeleting(false);
    }
  }

  async function create(template: ProductTemplate | null) {
    setError("");
    try {
      const p = await api.post<Project>("/api/projects", {
        name: template ? template.label : name.trim(),
        template: template ? template.key : null,
      });
      navigate(`/projects/${p.id}/overview`);
    } catch (e) {
      setError(errorText(e));
    }
  }

  return (
    <main className="page">
      <h1>Projects</h1>
      {error && <p className="error">{error}</p>}
      <section className="card">
        <h2>New project</h2>
        <div className="row">
          {templates.map((t) => (
            <button key={t.key} className="primary" onClick={() => create(t)}>
              Create {t.label} ({t.summary} template)
            </button>
          ))}
        </div>
        <div className="row">
          <input placeholder="Blank project name" value={name} onChange={(e) => setName(e.target.value)} />
          <button disabled={!name.trim()} onClick={() => create(null)}>
            Create blank project
          </button>
        </div>
      </section>
      <section>
        {projects === null ? (
          <p>Loading…</p>
        ) : projects.length === 0 ? (
          <p className="muted">No projects yet.</p>
        ) : (
          <ul className="project-list">
            {projects.map((p) => (
              <li key={p.id} className="card">
                <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline" }}>
                  <span>
                    <Link to={`/projects/${p.id}/overview`}>
                      <strong>{p.name}</strong>
                    </Link>
                    <span className="muted">
                      {" "}· {p.template ?? "blank"} · created {ukDateTime(p.created_at)} · updated {ukDateTime(p.updated_at)}
                    </span>
                  </span>
                  {confirming !== p.id && (
                    <button className="danger" onClick={() => setConfirming(p.id)} aria-label={`Delete ${p.name}`}>
                      Delete…
                    </button>
                  )}
                </div>
                <p className="muted small">{p.description}</p>
                {confirming === p.id && (
                  <div className="error" role="alertdialog" aria-label={`Confirm deleting ${p.name}`}>
                    <p>
                      Delete <strong>{p.name}</strong> (project #{p.id}, created {ukDateTime(p.created_at)}, last updated{" "}
                      {ukDateTime(p.updated_at)})?
                    </p>
                    <p className="small">
                      This permanently removes its parts, CAD versions and files, quotes, cost items, decisions, revisions and
                      uploaded images. It can't be undone.
                    </p>
                    <div className="row">
                      <button className="danger" disabled={deleting} onClick={() => remove(p)}>
                        {deleting ? "Deleting…" : `Delete ${p.name} permanently`}
                      </button>
                      <button disabled={deleting} onClick={() => setConfirming(null)}>Cancel</button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

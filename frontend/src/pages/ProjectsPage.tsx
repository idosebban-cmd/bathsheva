import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorText, type Project, type ProjectSummary } from "../api";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.get<ProjectSummary[]>("/api/projects").then(setProjects, (e) => setError(errorText(e)));
  }, []);

  async function create(template: "faro" | null) {
    setError("");
    try {
      const p = await api.post<Project>("/api/projects", {
        name: template === "faro" ? "Faro" : name.trim(),
        template,
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
          <button className="primary" onClick={() => create("faro")}>
            Create Faro (lighthouse lamp template)
          </button>
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
                <Link to={`/projects/${p.id}/overview`}>
                  <strong>{p.name}</strong>
                </Link>
                <span className="muted"> · {p.template ?? "blank"} · created {new Date(p.created_at).toLocaleDateString()}</span>
                <p className="muted small">{p.description}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { api, errorText, type Project } from "../api";

const TABS = [
  ["overview", "Overview"],
  ["parts", "Parts"],
] as const;

export default function ProjectLayout() {
  const { projectId } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    try {
      setProject(await api.get<Project>(`/api/projects/${projectId}`));
    } catch (e) {
      setError(errorText(e));
    }
  }, [projectId]);

  useEffect(() => {
    reload();
  }, [reload]);

  if (error) return <main className="page error">{error}</main>;
  if (!project) return <main className="page">Loading…</main>;

  return (
    <div className="project">
      <nav className="tabs">
        <span className="project-name">{project.name}</span>
        {TABS.map(([path, label]) => (
          <NavLink key={path} to={path}>
            {label}
          </NavLink>
        ))}
      </nav>
      <main className="page">
        <Outlet context={{ project, reload }} />
      </main>
    </div>
  );
}

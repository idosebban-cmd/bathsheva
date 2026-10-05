import { useCallback, useEffect, useState } from "react";
import { api, errorText, type RecommendationsResponse } from "../api";
import { UnverifiedBadge } from "../components/Badges";
import RecommendationCard from "../components/RecommendationCard";
import { useProject } from "../components/useProject";

export default function EngineeringPage() {
  const { project, reload: reloadProject } = useProject();
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setData(await api.get<RecommendationsResponse>(`/api/projects/${project.id}/recommendations`));
    } catch (e) {
      setError(errorText(e));
    }
  }, [project.id]);
  useEffect(() => {
    load();
  }, [load]);

  async function decideProject(topic: string, value: string) {
    await api.post(`/api/projects/${project.id}/decisions`, { topic, status: "accepted", chosen: { value } });
    await reloadProject();
    await load();
  }

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading…</p>;

  const safetyCount = data.recommendations.filter((r) => r.safety_flags.length).length;

  return (
    <div className="stack">
      <section className="card">
        <h2>Material and process recommendations</h2>
        <p className="small">
          Recommendations come from the rules engine (<code>backend/seed/rules</code>). Accept, edit or reject each one; accepted
          choices are written to the part and used for CAD wall-thickness limits.
        </p>
        <p className="notice small">
          <UnverifiedBadge /> All rule data is currently <strong>model-generated and unverified</strong>. Treat these as starting
          points to discuss with manufacturers. {safetyCount} part{safetyCount === 1 ? "" : "s"} have safety items that need human
          or manufacturer verification.
        </p>
        {!data.llm.enabled && (
          <p className="small muted">
            LLM disabled: recommendations are rules-only. Set ANTHROPIC_API_KEY to add AI explanations.
          </p>
        )}
      </section>

      {data.open_decisions.length > 0 && (
        <section className="card">
          <h2>Open project decisions</h2>
          {data.open_decisions.map((d) => (
            <div key={d.topic} className="open-decision">
              <p>
                <strong>{d.question}</strong> {d.open ? <span className="badge badge-unverified">Open</span> : <span className="badge badge-status-accepted">Decided: {d.current}</span>}
              </p>
              <p className="small muted">{d.impact}</p>
              <div className="row">
                {d.options.map((o) => (
                  <button key={o} onClick={() => decideProject(d.topic, o)} disabled={d.current === o}>
                    {o}
                  </button>
                ))}
                {!d.open && <button onClick={() => decideProject(d.topic, "undecided")}>Reopen</button>}
              </div>
            </div>
          ))}
        </section>
      )}

      {data.recommendations.map((rec) => (
        <RecommendationCard key={rec.part_id} rec={rec} projectId={project.id} llmEnabled={data.llm.enabled} onChanged={load} />
      ))}
    </div>
  );
}

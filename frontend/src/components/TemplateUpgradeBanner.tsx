import { useEffect, useState } from "react";
import { api, errorText, type TemplateUpgradePlan } from "../api";
import { useProject } from "./useProject";

/** Offers to bring a project created from an older template (e.g. the pre-prototype Faro) up to date. */
export default function TemplateUpgradeBanner() {
  const { project, reload } = useProject();
  const [plan, setPlan] = useState<TemplateUpgradePlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!project.template) return;
    api.get<TemplateUpgradePlan>(`/api/projects/${project.id}/template-upgrade`).then(setPlan).catch(() => setPlan(null));
  }, [project]);

  if (!plan || !plan.needed) return null;
  const quotes = plan.remove.reduce((n, r) => n + r.quotes, 0);

  async function upgrade() {
    if (!window.confirm(`Update this project to the current ${project.template} design? This removes ${plan!.remove.length} old parts`
      + (quotes ? ` (and their ${quotes} supplier quotes)` : "") + ", adds the new parts and resets the cost line items.")) return;
    setBusy(true);
    setError("");
    try {
      await api.post(`/api/projects/${project.id}/template-upgrade`, {});
      await reload();
      setPlan(null);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card notice">
      <h2>This project uses an older Faro design</h2>
      <p className="small">
        Faro now follows the approved prototype. Updating replaces the old parts ({plan.remove.map((r) => r.name).join(", ")}) with the
        new ones ({plan.add.map((a) => a.name).join(", ")}), sets the confirmed dimensions, cordless power and runtime target, records the
        accepted decisions and resets the cost line items. CAD history and revisions are kept; generate CAD again afterwards.
        {quotes > 0 && <b> {quotes} supplier quote(s) on removed parts will be deleted.</b>}
      </p>
      <button className="primary" disabled={busy} onClick={upgrade}>{busy ? "Updating…" : "Update to the current design"}</button>
      {error && <p className="error">{error}</p>}
    </section>
  );
}

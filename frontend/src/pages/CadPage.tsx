import { useEffect, useMemo, useRef, useState } from "react";
import { api, errorText, fileUrl, ApiError, type CadModel, type CadState, type ValidationResult } from "../api";
import { AssumptionBadge, UnverifiedBadge } from "../components/Badges";
import CadDownloads from "../components/CadDownloads";
import ModelViewer from "../components/ModelViewer";
import { useProject } from "../components/useProject";
import { useServerStale } from "../components/useServerStale";

export default function CadPage() {
  const { project } = useProject();
  const serverStale = useServerStale();
  const [state, setState] = useState<CadState | null>(null);
  const [params, setParams] = useState<Record<string, string>>({});
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const timer = useRef<number>();

  async function load() {
    try {
      const s = await api.get<CadState>(`/api/projects/${project.id}/cad`);
      setState(s);
      setParams(Object.fromEntries(Object.entries(s.parameters).map(([k, v]) => [k, String(v)])));
      setValidation(s.validation);
    } catch (e) {
      setError(errorText(e));
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  const numeric = useMemo(
    () => Object.fromEntries(Object.entries(params).map(([k, v]) => [k, v.trim() === "" ? null : Number(v)])),
    [params],
  );

  // Live validation (debounced).
  useEffect(() => {
    if (!state) return;
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(async () => {
      try {
        setValidation(await api.post<ValidationResult>(`/api/projects/${project.id}/cad/validate`, { parameters: numeric }));
      } catch (e) {
        setError(errorText(e));
      }
    }, 250);
    return () => window.clearTimeout(timer.current);
  }, [numeric, state, project.id]);

  async function generate() {
    setBusy(true);
    setError("");
    try {
      await api.post<CadModel>(`/api/projects/${project.id}/cad/generate`, { parameters: numeric });
      await load();
    } catch (e) {
      if (e instanceof ApiError && e.detail && typeof e.detail === "object" && "errors" in (e.detail as object)) {
        const d = e.detail as ValidationResult & { message: string };
        setValidation({ ok: false, errors: d.errors, warnings: d.warnings });
        setError(d.message);
      } else setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  if (error && !state) return <p className="error">{error}</p>;
  if (!state) return <p>Loading…</p>;

  const issuesFor = (key: string) => [...(validation?.errors ?? []), ...(validation?.warnings ?? [])].filter((i) => i.param === key);
  const general = [...(validation?.errors ?? []), ...(validation?.warnings ?? [])].filter((i) => !i.param);
  const groups = [...new Set(state.param_defs.map((d) => d.group))];
  const latest = state.latest;
  const glb = latest?.outputs.find((o) => o.part_key === null && o.format === "glb");
  const dirty = latest ? state.param_defs.some((d) => Number(params[d.key]) !== latest.parameters[d.key]) : true;
  const dimsAssumed = project.assumed_fields.includes("approx_dimensions");
  const changes = state.production_changes ?? [];

  return (
    <div className="cad-layout">
      <section className="card params">
        <h2>Parameters</h2>
        {dimsAssumed && (
          <p className="notice small">
            <AssumptionBadge /> {project.product?.label ?? "The product"}'s real dimensions are TBD. These defaults are placeholders for exploring proportions.
          </p>
        )}
        {groups.map((g) => (
          <fieldset key={g}>
            <legend>{g}</legend>
            {state.param_defs
              .filter((d) => d.group === g)
              .map((d) => {
                const issues = issuesFor(d.key);
                return (
                  <div className="param" key={d.key}>
                    <label htmlFor={`p-${d.key}`} title={d.help}>
                      {d.label}
                      {d.unit && <span className="muted"> ({d.unit})</span>}
                    </label>
                    <input
                      id={`p-${d.key}`}
                      type="number"
                      step={d.step}
                      min={d.min}
                      max={d.max}
                      value={params[d.key] ?? ""}
                      className={issues.some((i) => i.level === "error") ? "invalid" : ""}
                      onChange={(e) => setParams({ ...params, [d.key]: e.target.value })}
                    />
                    {issues.map((i, n) => (
                      <div key={n} className={`issue ${i.level}`}>
                        {i.message}
                      </div>
                    ))}
                  </div>
                );
              })}
          </fieldset>
        ))}
        {general.map((i, n) => (
          <div key={n} className={`issue ${i.level}`}>
            {i.message}
          </div>
        ))}
        <WallLimitNote state={state} />
        <div className="row sticky-actions">
          <button className="primary" disabled={busy || !validation?.ok} onClick={generate}>
            {busy ? "Generating…" : "Regenerate CAD"}
          </button>
          {validation && !validation.ok && (
            <span className="small issue error">
              {validation.errors.length} problem{validation.errors.length > 1 ? "s" : ""}: see highlighted fields
            </span>
          )}
          {latest && dirty && <span className="small muted">Parameters changed since v{latest.version}</span>}
        </div>
        {serverStale && (
          <p className="small issue warning">
            The server is running older code than the files on disk: restart the workbench before regenerating, or the
            model is built with the old version (for example without the knob emblem).
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2>Preview {latest && <span className="muted">· v{latest.version}</span>}</h2>
          {latest && <span className="small muted">generated {new Date(latest.created_at).toLocaleString()}</span>}
        </div>
        {glb ? (
          <ModelViewer url={fileUrl(glb.path)} product={state.product.key} />
        ) : (
          <div className="viewer empty">No CAD generated yet. Check the parameters and press "Regenerate CAD".</div>
        )}
        <p className="small muted">{state.product.cad_note}</p>
        {state.mass && (
          <p className={state.mass.status === "ok" ? "small" : "small warning-text"}>
            Estimated {state.product.noun} mass <b>{state.mass.total_kg.toFixed(2)} kg</b>
            {state.mass.target_kg ? ` vs target ${state.mass.target_kg} kg` : ""}
            {state.mass.status === "low" && (state.product.mass_part === "weight_plate"
              ? " — below target: thicken or enlarge the weight plate" : " — below target")}
            {state.mass.status === "high" && " — well above target"}
            {state.product.mass_part && state.mass.parts_kg[state.product.mass_part] !== undefined &&
              ` (${state.product.mass_part.replace("_", " ")} ${state.mass.parts_kg[state.product.mass_part].toFixed(2)} kg)`}.{" "}
            <span className="muted">{state.mass.note}</span>
          </p>
        )}
        {latest && <CadDownloads model={latest} projectId={project.id} />}
        {changes.length > 0 && (
          <details>
            <summary><strong>Where production differs from the 3D-printed prototype ({changes.length})</strong></summary>
            <table className="small changes">
              <thead><tr><th>Feature</th><th>Prototype</th><th>Production (proposed)</th></tr></thead>
              <tbody>
                {changes.map((c) => (
                  <tr key={c.feature}><td>{c.feature}</td><td>{c.prototype}</td><td>{c.production}</td></tr>
                ))}
              </tbody>
            </table>
          </details>
        )}
      </section>
    </div>
  );
}

function WallLimitNote({ state }: { state: CadState }) {
  const entries = Object.entries(state.wall_limits);
  if (!entries.length) return null;
  return (
    <div className="small muted">
      <strong>Wall limits applied:</strong>
      <ul>
        {entries.map(([part, l]) => (
          <li key={part}>
            {part.replace("_", " ")}: {l.process_name} {l.min}–{l.max} mm (typical {l.typical_min}–{l.typical_max}){" "}
            {!l.verified && <UnverifiedBadge />}
          </li>
        ))}
      </ul>
    </div>
  );
}

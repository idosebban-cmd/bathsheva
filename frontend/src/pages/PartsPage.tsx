import React, { useCallback, useEffect, useState } from "react";
import { api, errorText, type Part, type PartInput } from "../api";
import QuotesSection from "../components/QuotesSection";
import { useProject } from "../components/useProject";

export const MATERIAL_CATEGORIES = [
  ["aluminium", "Aluminium"],
  ["clear_polymer_or_glass", "Transparent (polymer or glass)"],
  ["electrical", "Electrical"],
  ["bought_in", "Bought-in / hardware"],
  ["other", "Other"],
] as const;

/** Parts ordered depth-first by parent, with their depth for indenting. */
export function partTree(parts: Part[]): { part: Part; depth: number }[] {
  const byParent = new Map<number | null, Part[]>();
  const ids = new Set(parts.map((p) => p.id));
  for (const p of parts) {
    const key = p.parent_id !== null && ids.has(p.parent_id) ? p.parent_id : null;
    byParent.set(key, [...(byParent.get(key) ?? []), p]);
  }
  const out: { part: Part; depth: number }[] = [];
  const walk = (parent: number | null, depth: number) => {
    for (const p of (byParent.get(parent) ?? []).sort((a, b) => a.sort_order - b.sort_order)) {
      out.push({ part: p, depth });
      walk(p.id, depth + 1);
    }
  };
  walk(null, 0);
  return out;
}

export function useParts(projectId: number) {
  const [parts, setParts] = useState<Part[]>([]);
  const reload = useCallback(async () => setParts(await api.get<Part[]>(`/api/projects/${projectId}/parts`)), [projectId]);
  useEffect(() => {
    reload();
  }, [reload]);
  return { parts, reload };
}

const BLANK: PartInput = {
  parent_id: null,
  cad_key: null,
  name: "New part",
  function: "",
  quantity: 1,
  material_category: "other",
  material: "",
  process: "",
  finish: "",
  traits: [],
  dimensions: "",
  tolerances: "",
  supplier_notes: "",
  cost_low: null,
  cost_high: null,
  open_questions: [],
  sort_order: 0,
};

export default function PartsPage() {
  const { project } = useProject();
  const { parts, reload } = useParts(project.id);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const selected = parts.find((p) => p.id === selectedId) ?? null;

  const [exportError, setExportError] = useState("");

  // Check first so a "generate CAD first" error is shown instead of downloading an error page.
  async function exportPack(e: React.MouseEvent<HTMLAnchorElement>) {
    e.preventDefault();
    setExportError("");
    const url = `/api/projects/${project.id}/quote-pack.zip`;
    const res = await fetch(url);
    if (!res.ok) {
      setExportError((await res.json().catch(() => ({ detail: res.statusText }))).detail);
      return;
    }
    const blob = await res.blob();
    const name = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? "quote_pack.zip";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function addPart() {
    const p = await api.post<Part>(`/api/projects/${project.id}/parts`, BLANK);
    await reload();
    setSelectedId(p.id);
  }

  return (
    <div className="stack">
      <div className="split">
        <section className="card">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <h2>Parts</h2>
            <div className="row">
              <a href={`/api/projects/${project.id}/quote-pack.zip`} onClick={exportPack}>
                <button title="Zip of each part's STEP file plus a README with material, finish and quantity from the BOM">
                  Export parts for quoting
                </button>
              </a>
              <button onClick={addPart}>+ Add part</button>
            </div>
          </div>
          {exportError && <p className="error">{exportError}</p>}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Qty</th>
                  <th>Material</th>
                  <th>Process</th>
                  <th>Finish</th>
                  <th>CAD</th>
                </tr>
              </thead>
              <tbody>
                {partTree(parts).map(({ part, depth }) => (
                  <tr key={part.id} className={part.id === selectedId ? "selected" : "clickable"} onClick={() => setSelectedId(part.id)}>
                    <td style={{ paddingLeft: `${0.5 + depth * 1.25}rem` }}>{part.name}</td>
                    <td>{part.quantity}</td>
                    <td>{part.material || <span className="muted">—</span>}</td>
                    <td>{part.process || <span className="muted">—</span>}</td>
                    <td>{part.finish || <span className="muted">—</span>}</td>
                    <td className="muted small">{part.cad_key ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted small">
            Material and process are blank until you accept or edit a recommendation on the Engineering tab, or type them here.
          </p>
        </section>
        {selected ? (
          <PartEditor
            key={selected.id}
            part={selected}
            parts={parts}
            onSaved={reload}
            onDeleted={async () => {
              setSelectedId(null);
              await reload();
            }}
          />
        ) : (
          <section className="card muted">Select a part to edit it.</section>
        )}
      </div>
      {selected && <QuotesSection key={`q-${selected.id}`} part={selected} />}
    </div>
  );
}

function PartEditor({ part, parts, onSaved, onDeleted }: { part: Part; parts: Part[]; onSaved: () => Promise<void>; onDeleted: () => Promise<void> }) {
  const [draft, setDraft] = useState<Part>(part);
  const [traitsText, setTraitsText] = useState(part.traits.join(", "));
  const [status, setStatus] = useState("");
  const set = <K extends keyof Part>(k: K, v: Part[K]) => setDraft((d) => ({ ...d, [k]: v }));

  async function save() {
    setStatus("Saving…");
    try {
      const { id: _id, project_id: _pid, ...body } = draft;
      void _id;
      void _pid;
      await api.patch(`/api/projects/${part.project_id}/parts/${part.id}`, {
        ...body,
        traits: traitsText.split(",").map((s) => s.trim()).filter(Boolean),
        open_questions: body.open_questions.map((s) => s.trim()).filter(Boolean),
      });
      await onSaved();
      setStatus("Saved");
    } catch (e) {
      setStatus(errorText(e));
    }
  }

  async function remove() {
    if (!confirm(`Delete part "${part.name}"?`)) return;
    await api.del(`/api/projects/${part.project_id}/parts/${part.id}`);
    await onDeleted();
  }

  const text = (k: "name" | "function" | "material" | "process" | "finish" | "dimensions" | "tolerances" | "supplier_notes", label: string, multiline = false) => (
    <div className="field">
      <label>{label}</label>
      {multiline ? (
        <textarea rows={2} value={draft[k]} onChange={(e) => set(k, e.target.value)} />
      ) : (
        <input value={draft[k]} onChange={(e) => set(k, e.target.value)} />
      )}
    </div>
  );
  const money = (v: string) => (v.trim() === "" ? null : Number(v));

  return (
    <section className="card">
      <h2>{part.name}</h2>
      {text("name", "Name")}
      {text("function", "Function", true)}
      <div className="row">
        <div className="field">
          <label>Quantity</label>
          <input type="number" min={1} value={draft.quantity} onChange={(e) => set("quantity", Number(e.target.value))} />
        </div>
        <div className="field">
          <label>Parent</label>
          <select value={draft.parent_id ?? ""} onChange={(e) => set("parent_id", e.target.value ? Number(e.target.value) : null)}>
            <option value="">(top level)</option>
            {parts
              .filter((p) => p.id !== part.id)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
          </select>
        </div>
        <div className="field">
          <label>Material family</label>
          <select value={draft.material_category} onChange={(e) => set("material_category", e.target.value)}>
            {MATERIAL_CATEGORIES.map(([k, l]) => (
              <option key={k} value={k}>
                {l}
              </option>
            ))}
          </select>
        </div>
      </div>
      {text("material", "Material")}
      {text("process", "Manufacturing process")}
      {text("finish", "Finish")}
      {text("dimensions", "Dimensions (notes; generated sizes are in the BOM)", true)}
      {text("tolerances", "Tolerances", true)}
      {text("supplier_notes", "Supplier notes", true)}
      <div className="row">
        <div className="field">
          <label>Cost estimate low (GBP)</label>
          <input type="number" min={0} step="0.01" placeholder="TBD" value={draft.cost_low ?? ""} onChange={(e) => set("cost_low", money(e.target.value))} />
        </div>
        <div className="field">
          <label>Cost estimate high (GBP)</label>
          <input type="number" min={0} step="0.01" placeholder="TBD" value={draft.cost_high ?? ""} onChange={(e) => set("cost_high", money(e.target.value))} />
        </div>
      </div>
      <div className="field">
        <label>Geometry traits (comma separated; used by the rules engine)</label>
        <input value={traitsText} onChange={(e) => setTraitsText(e.target.value)} />
      </div>
      <div className="field">
        <label>Open questions (one per line)</label>
        <textarea rows={3} value={draft.open_questions.join("\n")} onChange={(e) => set("open_questions", e.target.value.split("\n"))} />
      </div>
      <div className="row">
        <button className="primary" onClick={save}>
          Save part
        </button>
        <button className="danger" onClick={remove}>
          Delete
        </button>
        <span className="muted">{status}</span>
      </div>
    </section>
  );
}

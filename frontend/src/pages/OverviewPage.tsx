import { useEffect, useState, type ReactNode } from "react";
import { api, errorText, fileUrl, type Project, type Requirements } from "../api";
import { AssumptionBadge } from "../components/Badges";
import { useProject } from "../components/useProject";

type ListField =
  | "intended_markets"
  | "preferred_materials"
  | "preferred_finishes"
  | "functional_requirements"
  | "environmental_requirements";

const LIST_FIELDS: [ListField, string][] = [
  ["intended_markets", "Intended markets"],
  ["preferred_materials", "Preferred materials"],
  ["preferred_finishes", "Preferred finishes"],
  ["functional_requirements", "Functional requirements"],
  ["environmental_requirements", "Environmental requirements"],
];

const num = (v: string): number | null => (v.trim() === "" ? null : Number(v));
const show = (v: number | null | undefined) => (v === null || v === undefined ? "" : String(v));

export default function OverviewPage() {
  const { project, reload } = useProject();
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description);
  const [req, setReq] = useState<Requirements>(project.requirements);
  const [assumed, setAssumed] = useState<string[]>(project.assumed_fields);
  const [status, setStatus] = useState("");

  useEffect(() => {
    setName(project.name);
    setDescription(project.description);
    setReq(project.requirements);
    setAssumed(project.assumed_fields);
  }, [project]);

  const toggleAssumed = (field: string) =>
    setAssumed((a) => (a.includes(field) ? a.filter((f) => f !== field) : [...a, field]));

  async function save() {
    setStatus("Saving…");
    try {
      await api.patch<Project>(`/api/projects/${project.id}`, {
        name,
        description,
        requirements: req,
        assumed_fields: assumed,
      });
      await reload();
      setStatus("Saved");
    } catch (e) {
      setStatus(errorText(e));
    }
  }

  // Called as a function (not as a component) so inputs keep focus across re-renders.
  const renderField = ({ field, label, children }: { field: string; label: string; children: ReactNode }) => (
    <div className="field" key={field}>
      <label>
        {label} {assumed.includes(field) && <AssumptionBadge />}
      </label>
      {children}
      <label className="small muted checkbox">
        <input type="checkbox" checked={assumed.includes(field)} onChange={() => toggleAssumed(field)} /> placeholder /
        assumption
      </label>
    </div>
  );

  return (
    <div className="stack">
      <section className="card">
        <h2>Product</h2>
        <div className="field">
          <label>Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label>Description</label>
          <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
      </section>

      <section className="card">
        <h2>Requirements</h2>
        <p className="muted small">Empty means TBD. Fields marked as assumptions are placeholders until you confirm them.</p>
        <div className="grid">
          {renderField({ field: "approx_dimensions", label: "Approximate dimensions (mm): H × W × D", children: (<>
            <div className="row">
              {(["height_mm", "width_mm", "depth_mm"] as const).map((k) => (
                <input
                  key={k}
                  type="number"
                  placeholder="TBD"
                  value={show(req.approx_dimensions[k])}
                  onChange={(e) => setReq({ ...req, approx_dimensions: { ...req.approx_dimensions, [k]: num(e.target.value) } })}
                />
              ))}
            </div>
          </>) })}
          {renderField({ field: "target_retail_price", label: `Target retail price (${req.target_retail_price.currency})`, children: (<>
            <input
              type="number"
              placeholder="TBD"
              value={show(req.target_retail_price.amount)}
              onChange={(e) => setReq({ ...req, target_retail_price: { ...req.target_retail_price, amount: num(e.target.value) } })}
            />
          </>) })}
          {renderField({ field: "production_volume", label: "Expected production volume (units / year)", children: (<>
            <input
              type="number"
              placeholder="TBD"
              value={show(req.production_volume)}
              onChange={(e) => setReq({ ...req, production_volume: num(e.target.value) })}
            />
          </>) })}
          {renderField({ field: "target_unit_cost", label: `Target unit manufacturing cost (${req.target_unit_cost.currency})`, children: (<>
            <input
              type="number"
              placeholder="TBD"
              value={show(req.target_unit_cost.amount)}
              onChange={(e) => setReq({ ...req, target_unit_cost: { ...req.target_unit_cost, amount: num(e.target.value) } })}
            />
          </>) })}
          {renderField({ field: "power_type", label: "Power type", children: (<>
            <select value={req.power_type} onChange={(e) => setReq({ ...req, power_type: e.target.value as Requirements["power_type"] })}>
              <option value="undecided">Undecided (open decision)</option>
              <option value="mains">Mains</option>
              <option value="battery">Rechargeable battery</option>
              <option value="passive">Passive (no power)</option>
            </select>
          </>) })}
          {LIST_FIELDS.map(([field, label]) => (
            renderField({ field, label: `${label} (one per line)`, children: (<>
              <textarea
                rows={3}
                value={req[field].join("\n")}
                onChange={(e) => setReq({ ...req, [field]: e.target.value.split("\n") })}
                onBlur={(e) => setReq({ ...req, [field]: e.target.value.split("\n").map((s) => s.trim()).filter(Boolean) })}
              />
            </>) })
          ))}
        </div>
        <div className="row">
          <button className="primary" onClick={save}>
            Save
          </button>
          <span className="muted">{status}</span>
        </div>
      </section>

      <ImagesSection />
    </div>
  );
}

function ImagesSection() {
  const { project, reload } = useProject();
  const [kind, setKind] = useState("concept");
  const [error, setError] = useState("");

  async function upload(files: FileList | null) {
    if (!files) return;
    setError("");
    try {
      for (const file of Array.from(files)) {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("kind", kind);
        await api.post(`/api/projects/${project.id}/images`, fd);
      }
      await reload();
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function remove(id: number) {
    await api.del(`/api/projects/${project.id}/images/${id}`);
    await reload();
  }

  return (
    <section className="card">
      <h2>Concept renders and reference images</h2>
      <div className="row">
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="concept">Concept render</option>
          <option value="reference">Reference image</option>
        </select>
        <input type="file" accept="image/*" multiple onChange={(e) => upload(e.target.files)} />
      </div>
      {error && <p className="error">{error}</p>}
      <div className="gallery">
        {project.images.map((img) => (
          <figure key={img.id}>
            <img src={fileUrl(img.path)} alt={img.filename} />
            <figcaption>
              <span className="badge">{img.kind}</span> {img.filename}
              <button className="link" onClick={() => remove(img.id)}>
                remove
              </button>
            </figcaption>
          </figure>
        ))}
        {project.images.length === 0 && <p className="muted">No images yet.</p>}
      </div>
    </section>
  );
}

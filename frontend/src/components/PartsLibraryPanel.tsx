import { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import { describeShape, dragPayload, lineShape, PART_DRAG_TYPE, partShape, type ShapeSpec } from "../conceptShapes";
import { allParts, matchesSearch, newLine, priceLabel, unitFor, unitLabel, type Library, type LibraryPart } from "../standardParts";
import { AvailabilityBadge, PriceCell } from "../pages/StandardPartsPage";
import { geometriesFor } from "./conceptMeshes";
import { lookMaterial } from "./materials";
import { ViewerStage } from "./ModelViewer";

/** "farnell.com" for a link, or the text itself if it doesn't parse. */
function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** The part's shape on its own, to turn round in the preview. */
function PreviewShape({ spec, look }: { spec: ShapeSpec | null; look: string }) {
  const key = JSON.stringify(spec);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const geometries = useMemo(() => geometriesFor(spec), [key]);
  const material = useMemo(() => lookMaterial(spec ? look : "placeholder"), [spec, look]);
  useEffect(() => () => geometries.forEach((g) => g.dispose()), [geometries]);
  useEffect(() => () => material.dispose(), [material]);
  return (
    <>
      {geometries.map((g: THREE.BufferGeometry, i) => (
        <mesh key={i} geometry={g} material={material} castShadow receiveShadow />
      ))}
    </>
  );
}

function PartPreview({ part, option, onOption, onAdd }: {
  part: LibraryPart;
  option: number;
  onOption: (option: number) => void;
  onAdd: () => void;
}) {
  const stock = partShape(part, option);
  const drawn = lineShape(newLine(part, option), part); // what adding it draws (a sized part: one 100 mm piece)
  const unit = unitFor(part, option);
  return (
    <div className="sp-preview">
      <ViewerStage fitKey={`${part.id}:${option}`} observe={false} shadowScale={300} margin={1.5} className="sp-preview-stage">
        <PreviewShape spec={drawn} look={stock?.look ?? part.look} />
      </ViewerStage>
      <div className="sp-preview-body small">
        <strong>{part.name}</strong> <AvailabilityBadge part={part} />
        {part.options.length > 1 && (
          <label className="sp-preview-variant">
            <span className="muted">Variant</span>
            <select value={option} onChange={(e) => onOption(Number(e.target.value))}>
              {part.options.map((o, k) => (
                <option key={k} value={k}>
                  {priceLabel(o)}
                  {o.label ? ` (${o.label})` : ""}
                </option>
              ))}
            </select>
          </label>
        )}
        <dl className="sp-preview-facts">
          <dt>Sizes</dt>
          <dd>{part.sizes || "Not stated"}</dd>
          <dt>Drawn as</dt>
          <dd>
            {stock ? describeShape(stock) : "a placeholder box (no sizes in the library)"}
            {stock?.assumed && <div className="muted">Assumed: {stock.assumed}</div>}
            {stock?.source && (
              <div className="muted">
                Sizes from{" "}
                {/^https?:\/\//.test(stock.source) ? (
                  <a href={stock.source} target="_blank" rel="noreferrer">
                    {hostOf(stock.source)} ↗
                  </a>
                ) : (
                  stock.source
                )}
              </div>
            )}
            {unit && drawn && (
              <div className="muted">
                Priced per {unitLabel(unit)}; added as one piece, {describeShape(drawn)} (change the size in the parts table)
              </div>
            )}
          </dd>
          <dt>Material</dt>
          <dd>{part.material || "Not stated"}</dd>
          <dt>Price</dt>
          <dd>
            <PriceCell part={part} />
          </dd>
          <dt>Supplier</dt>
          <dd>
            {part.supplier}
            {part.links.map((l) => (
              <div key={l.url}>
                <a href={l.url} target="_blank" rel="noreferrer">
                  {l.label === "link" ? "Product page" : l.label} ↗
                </a>
              </div>
            ))}
            {part.source_files.length > 0 && <div className="muted">From {part.source_files.join(", ")}</div>}
          </dd>
        </dl>
        <button className="primary" onClick={onAdd}>
          Add to concept
        </button>
      </div>
    </div>
  );
}

/**
 * The parts library beside the concept's 3D view: search it or browse by category, preview a part (hover or select
 * it), then drag it into the view or press Add.
 */
export default function PartsLibraryPanel({ library, onAdd }: {
  library: Library;
  onAdd: (part: LibraryPart, option: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState(""); // "" all, "s:<n>" a section, "u:<n>" a subsection
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [option, setOption] = useState(0);

  const groups = useMemo(() => {
    const out: { key: string; title: string; parts: LibraryPart[] }[] = [];
    for (const s of library.sections) {
      if (category.startsWith("s:") && category !== `s:${s.number}`) continue;
      for (const sub of s.subsections) {
        if (category.startsWith("u:") && category !== `u:${sub.number}`) continue;
        const parts = sub.parts.filter((p) => matchesSearch(p, query));
        if (parts.length) out.push({ key: sub.number, title: `${sub.number} ${sub.title}`, parts });
      }
    }
    return out;
  }, [library, query, category]);
  const byId = useMemo(() => new Map(allParts(library).map((p) => [p.id, p])), [library]);
  const count = groups.reduce((n, g) => n + g.parts.length, 0);
  const shown = byId.get(previewId ?? selectedId ?? "");

  const preview = (id: string) => {
    if (id !== previewId) setOption(0);
    setPreviewId(id);
  };

  return (
    <div className="sp-library-panel">
      <h3>Parts library</h3>
      <input type="search" placeholder="Search (e.g. brass tube, opal globe)" value={query} onChange={(e) => setQuery(e.target.value)} />
      <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
        <option value="">All categories</option>
        {library.sections.map((s) => (
          <optgroup key={s.number} label={`${s.number}. ${s.title}`}>
            <option value={`s:${s.number}`}>All of {s.title}</option>
            {s.subsections.map((sub) => (
              <option key={sub.number} value={`u:${sub.number}`}>
                {sub.number} {sub.title}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <p className="small muted">
        {count} part{count === 1 ? "" : "s"}. Hover or click one to preview it; drag it into the 3D view to add it.
      </p>
      {/* Leaving the list goes back to the selected part, or keeps the last one hovered, so it can be turned round. */}
      <div className="sp-library-list" onMouseLeave={() => selectedId && preview(selectedId)}>
        {groups.map((g) => (
          <div key={g.key}>
            <div className="sp-library-group small">{g.title}</div>
            {g.parts.map((p) => (
              <div
                key={p.id}
                className={`sp-library-item${p.id === shown?.id ? " active" : ""}`}
                draggable
                tabIndex={0}
                role="button"
                aria-label={`${p.name}, ${p.supplier}. Drag into the 3D view, or press Enter to preview`}
                onMouseEnter={() => preview(p.id)}
                onFocus={() => preview(p.id)}
                onClick={() => {
                  preview(p.id);
                  setSelectedId(p.id);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setSelectedId(p.id);
                }}
                onDragStart={(e) => {
                  e.dataTransfer.effectAllowed = "copy";
                  e.dataTransfer.setData(PART_DRAG_TYPE, dragPayload(p.id, p.id === shown?.id ? option : 0));
                  e.dataTransfer.setData("text/plain", p.name);
                }}>
                <div className="sp-library-name">{p.name}</div>
                <div className="small muted">
                  {p.options[0] ? priceLabel(p.options[0]) : "No listed price"} · {p.supplier}
                </div>
              </div>
            ))}
          </div>
        ))}
        {count === 0 && <p className="small muted">No parts match.</p>}
      </div>
      {shown ? (
        <PartPreview part={shown} option={option} onOption={setOption} onAdd={() => onAdd(shown, option)} />
      ) : (
        <p className="small muted sp-preview-empty">Hover over or select a part to see its shape, sizes, price and supplier.</p>
      )}
    </div>
  );
}

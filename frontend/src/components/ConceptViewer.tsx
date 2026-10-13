import { useEffect, useMemo } from "react";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import {
  DEFAULT_VIEW,
  globeGeometry,
  layoutConcept,
  PLACEHOLDER_SIZE,
  viewOf,
  type LineView,
  type Placed,
  type ShapeSpec,
} from "../conceptShapes";
import type { ConceptLine, LibraryPart } from "../standardParts";
import { lookMaterial } from "./materials";
import { ViewerStage } from "./ModelViewer";

const SEGMENTS = 64;
const deg = THREE.MathUtils.degToRad;

/** Meshes for a shape, its bottom at y = 0 and centred on the vertical axis. */
function geometriesFor(spec: ShapeSpec | null): THREE.BufferGeometry[] {
  const lathe = (pts: [number, number][]) => new THREE.LatheGeometry(pts.map(([x, y]) => new THREE.Vector2(x, y)), SEGMENTS);
  const lift = (g: THREE.BufferGeometry, y: number) => g.translate(0, y, 0);
  if (!spec) return [lift(new THREE.BoxGeometry(PLACEHOLDER_SIZE, PLACEHOLDER_SIZE, PLACEHOLDER_SIZE), PLACEHOLDER_SIZE / 2)];
  switch (spec.shape) {
    case "tube":
    case "ring": {
      const ro = spec.od / 2, ri = spec.id / 2, h = spec.shape === "tube" ? spec.length : spec.thickness;
      if (ri <= 0) return [lift(new THREE.CylinderGeometry(ro, ro, h, SEGMENTS), h / 2)];
      return [lathe([[ri, 0], [ro, 0], [ro, h], [ri, h], [ri, 0]])];
    }
    case "rod":
      return [lift(new THREE.CylinderGeometry(spec.d / 2, spec.d / 2, spec.length, SEGMENTS), spec.length / 2)];
    case "cylinder":
      return [lift(new THREE.CylinderGeometry(spec.d / 2, spec.d / 2, spec.height, SEGMENTS), spec.height / 2)];
    case "disc":
      return [lift(new THREE.CylinderGeometry(spec.d / 2, spec.d / 2, spec.thickness, SEGMENTS), spec.thickness / 2)];
    case "bar":
    case "strip":
      return [lift(new THREE.BoxGeometry(spec.width, spec.length, spec.thickness), spec.length / 2)];
    case "sheet":
      return [lift(new THREE.BoxGeometry(spec.width, spec.thickness, spec.height), spec.thickness / 2)];
    case "box":
      return [lift(new THREE.BoxGeometry(spec.width, spec.height, spec.depth), spec.height / 2)];
    case "dome": {
      // A half-ellipsoid shell, open at the bottom and (if it has one) at the fitter hole on top.
      const r = spec.d / 2, h = spec.height, open = Math.min((spec.opening ?? 0) / 2, r * 0.95);
      const pts: [number, number][] = [];
      for (let i = 0; i <= 32; i++) {
        const t = (i / 32) * (Math.PI / 2);
        const x = r * Math.cos(t);
        if (x < open) {
          pts.push([open, h * Math.sqrt(1 - (open / r) ** 2)]);
          break;
        }
        pts.push([Math.max(x, 0.001), h * Math.sin(t)]);
      }
      return [lathe(pts)];
    }
    case "cone":
      return [lathe([[spec.d_bottom / 2, 0], [Math.max(spec.d_top / 2, 0.001), spec.height]])];
    case "sphere":
      return [lift(new THREE.SphereGeometry(spec.d / 2, 48, 32), spec.d / 2)];
    case "globe": {
      const g = globeGeometry(spec);
      return [
        lathe([[g.nr, 0], [g.nr, spec.neck_height]]),
        lift(new THREE.SphereGeometry(g.r, 48, 32, 0, Math.PI * 2, 0, g.openAngle), g.centre),
      ];
    }
  }
}

function PlacedPart({ placed, selected, materials, highlight, onSelect }: {
  placed: Placed;
  selected: boolean;
  materials: (look: string) => THREE.Material;
  highlight: THREE.Material;
  onSelect: (index: number) => void;
}) {
  const key = JSON.stringify(placed.spec);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const geometries = useMemo(() => geometriesFor(placed.spec), [key]);
  useEffect(() => () => geometries.forEach((g) => g.dispose()), [geometries]);
  const { view, height, total, base } = placed;
  const material = materials(placed.spec ? placed.look : "placeholder");
  return (
    <>
      {placed.instances.map((inst, k) => (
        // Outer group: the copy's angle round the axis. Inner: the line's offset and rotation about the centre of
        // its stacked pieces, so a tilted stack stays together.
        <group key={k} rotation-y={deg(inst.angle)}
          onClick={(e) => {
            e.stopPropagation();
            onSelect(placed.index);
          }}>
          <group position={[view.dx, base + total / 2 + view.dy, view.dz]} rotation={[deg(view.rx), deg(view.ry), deg(view.rz)]}>
            {Array.from({ length: placed.pieces }, (_, piece) => (
              <group key={piece} position={[0, -total / 2 + piece * height, 0]}>
                {geometries.map((g, i) => (
                  <mesh key={i} geometry={g} material={material} castShadow receiveShadow>
                    {selected && <mesh geometry={g} material={highlight} scale={1.001} />}
                  </mesh>
                ))}
                {!placed.spec && k === 0 && piece === placed.pieces - 1 && (
                  <Html position={[0, PLACEHOLDER_SIZE + 6, 0]} center className="sp-3d-label">
                    {placed.index + 1}. {placed.name}
                  </Html>
                )}
              </group>
            ))}
          </group>
        </group>
      ))}
    </>
  );
}

function ViewNumber({ label, value, step, onChange }: { label: string; value: number; step: number; onChange: (v: number) => void }) {
  return (
    <label className="sp-view-field">
      <span>{label}</span>
      <input type="number" step={step} value={value} onChange={(e) => onChange(Number(e.target.value) || 0)} />
    </label>
  );
}

/**
 * 3D view of a concept as it's built: each line's part drawn from its library shape, stacked up the vertical
 * axis in table order, with controls to move, turn and repeat the selected part. Orbit, zoom and pan with the
 * mouse; "Fit" brings everything back into view.
 */
export default function ConceptViewer({
  lines,
  parts,
  selected,
  onSelect,
  onViewChange,
}: {
  lines: ConceptLine[];
  parts: Map<string, LibraryPart>;
  selected: number | null;
  onSelect: (index: number | null) => void;
  onViewChange: (index: number, view: LineView) => void;
}) {
  const placed = useMemo(() => layoutConcept(lines, parts), [lines, parts]);
  const materials = useMemo(() => {
    const cache = new Map<string, THREE.Material>();
    return (look: string) => {
      if (!cache.has(look)) cache.set(look, lookMaterial(look));
      return cache.get(look)!;
    };
  }, []);
  const highlight = useMemo(
    () => new THREE.MeshBasicMaterial({ color: "#2f5d62", transparent: true, opacity: 0.22, depthWrite: false }),
    [],
  );
  const sel = selected !== null ? placed[selected] : undefined;
  const placeholders = placed.filter((p) => !p.spec);
  const assumed = placed.filter((p) => p.spec && p.assumed);
  const set = (patch: Partial<LineView>) => sel && onViewChange(sel.index, { ...viewOf(lines[sel.index]), ...patch });

  return (
    <div className="sp-3d">
      {/* Refit when parts are added or removed; edits to a part's place leave the camera where it is. */}
      <ViewerStage observe={false} fitKey={`${lines.length}`} onPointerMissed={() => onSelect(null)} shadowScale={900}
        margin={1.6} className="sp-3d-stage">
        {placed.map((p) => (
          <PlacedPart key={p.index} placed={p} selected={p.index === selected} materials={materials} highlight={highlight}
            onSelect={onSelect} />
        ))}
        {placed.length === 0 && (
          <Html center className="sp-3d-label">
            Add parts to see them here
          </Html>
        )}
      </ViewerStage>
      <p className="small muted">Drag to orbit, scroll to zoom, right-drag to pan. Click a part to select it.</p>

      <div className="sp-3d-controls">
        <label className="field">
          <span>Part</span>
          <select value={selected ?? ""} onChange={(e) => onSelect(e.target.value === "" ? null : Number(e.target.value))}>
            <option value="">Select a part to place it</option>
            {placed.map((p) => (
              <option key={p.index} value={p.index}>
                {p.index + 1}. {p.name}
              </option>
            ))}
          </select>
        </label>
        {sel && (
          <>
            <p className="small muted">
              {sel.pieces > 1 ? `${sel.pieces} pieces stacked, ${+sel.height.toFixed(1)} mm each, ${+sel.total.toFixed(1)} mm in all. ` : `${+sel.height.toFixed(1)} mm tall. `}
              {sel.instances.length > 1 && `${sel.instances.length} copies round the centre, one piece each. `}
              Its place in the stack starts at {+sel.base.toFixed(1)} mm, so with the up/down offset its bottom is at{" "}
              {+(sel.base + sel.view.dy).toFixed(1)} mm (the ground is 0).
            </p>
            <div className="sp-view-grid">
              <ViewNumber label="Up / down (mm)" step={1} value={sel.view.dy} onChange={(v) => set({ dy: v })} />
              <ViewNumber label="Left / right (mm)" step={1} value={sel.view.dx} onChange={(v) => set({ dx: v })} />
              <ViewNumber label="Front / back (mm)" step={1} value={sel.view.dz} onChange={(v) => set({ dz: v })} />
              <ViewNumber label="Tilt ↕ (°)" step={15} value={sel.view.rx} onChange={(v) => set({ rx: v })} />
              <ViewNumber label="Turn ↻ (°)" step={15} value={sel.view.ry} onChange={(v) => set({ ry: v })} />
              <ViewNumber label="Tilt ↔ (°)" step={15} value={sel.view.rz} onChange={(v) => set({ rz: v })} />
              <label className="sp-view-field">
                <span>Repeat round the centre</span>
                <input type="number" min={1} max={64} step={1} value={sel.view.repeat}
                  onChange={(e) => set({ repeat: Math.min(64, Math.max(1, Math.round(Number(e.target.value) || 1))) })} />
              </label>
              {sel.sheetPart && (
                <label className="sp-view-field">
                  <span>Sheet drawn as</span>
                  <select value={sel.view.form} onChange={(e) => set({ form: e.target.value as LineView["form"] })}>
                    <option value="auto">Flat sheet</option>
                    <option value="disc">Cut disc</option>
                    <option value="rolled">Rolled tube</option>
                  </select>
                </label>
              )}
            </div>
            <label className="checkbox small">
              <input type="checkbox" checked={sel.view.stack} onChange={(e) => set({ stack: e.target.checked })} />
              The next part sits on top of this one (untick for a part that sits inside another)
            </label>
            {sel.view.repeat > 1 && Math.hypot(sel.view.dx, sel.view.dz) === 0 && (
              <p className="small notice">The copies overlap: set a left/right or front/back offset to space them round the centre.</p>
            )}
            <button className="link" onClick={() => onViewChange(sel.index, DEFAULT_VIEW)}>
              Reset this part&apos;s place
            </button>
          </>
        )}
      </div>

      {placeholders.length > 0 && (
        <div className="small">
          <strong>Drawn as placeholders</strong> (no sizes in the library):
          <ul className="sp-3d-list">
            {placeholders.map((p) => (
              <li key={p.index}>
                {p.index + 1}. {p.name}
              </li>
            ))}
          </ul>
        </div>
      )}
      {assumed.length > 0 && (
        <div className="small muted">
          <strong>Sizes partly assumed:</strong>
          <ul className="sp-3d-list">
            {assumed.map((p) => (
              <li key={p.index}>
                {p.index + 1}. {p.name}: {p.assumed}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

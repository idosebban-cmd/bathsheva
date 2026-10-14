import { useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import { Html } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import {
  DEFAULT_VIEW,
  layoutConcept,
  MADE_SHAPES,
  madeFrom,
  PART_DRAG_TYPE,
  PLACEHOLDER_SIZE,
  readDragPayload,
  viewOf,
  type LineView,
  type MadeKind,
  type Placed,
  type ShapeSpec,
} from "../conceptShapes";
import type { ConceptLine, LibraryPart } from "../standardParts";
import { geometriesFor } from "./conceptMeshes";
import { lookMaterial } from "./materials";
import { ViewerStage } from "./ModelViewer";

const deg = THREE.MathUtils.degToRad;

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
  const [hovered, setHovered] = useState(false);
  const { view, height, total, base } = placed;
  const material = materials(placed.spec ? placed.look : "placeholder");
  // A placeholder's name shows while the pointer is over it or it's selected, so labels don't crowd the view.
  const showLabel = !placed.spec && (hovered || selected);
  return (
    <>
      {placed.instances.map((inst, k) => (
        // Outer group: the copy's angle round the axis. Inner: the line's offset and rotation about the centre of
        // its stacked pieces, so a tilted stack stays together.
        <group key={k} rotation-y={deg(inst.angle)} userData={{ lineIndex: placed.index }}
          onClick={(e) => {
            e.stopPropagation();
            onSelect(placed.index);
          }}
          onPointerOver={(e) => {
            e.stopPropagation();
            setHovered(true);
          }}
          onPointerOut={() => setHovered(false)}>
          <group position={[view.dx, base + total / 2 + view.dy, view.dz]} rotation={[deg(view.rx), deg(view.ry), deg(view.rz)]}>
            {Array.from({ length: placed.pieces }, (_, piece) => (
              <group key={piece} position={[0, -total / 2 + piece * height, 0]}>
                {geometries.map((g, i) => (
                  <mesh key={i} geometry={g} material={material} castShadow receiveShadow>
                    {selected && <mesh geometry={g} material={highlight} scale={1.001} />}
                  </mesh>
                ))}
                {showLabel && k === 0 && piece === placed.pieces - 1 && (
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

const MADE_LABELS: Record<string, string> = {
  d: "Diameter", od: "Outside Ø", id: "Bore Ø", height: "Height", thickness: "Thickness", length: "Length",
  width: "Width", depth: "Depth", d_bottom: "Bottom Ø", d_top: "Top Ø",
};

type Pick = (clientX: number, clientY: number) => number | null;

/** Inside the canvas: works out which line's part is under a screen point (for dropping a part onto it). */
function DropPicker({ pickRef }: { pickRef: MutableRefObject<Pick | null> }) {
  const { camera, scene, gl } = useThree();
  useEffect(() => {
    const raycaster = new THREE.Raycaster();
    pickRef.current = (x, y) => {
      const r = gl.domElement.getBoundingClientRect();
      raycaster.setFromCamera(new THREE.Vector2(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1), camera);
      for (const hit of raycaster.intersectObjects(scene.children, true)) {
        for (let o: THREE.Object3D | null = hit.object; o; o = o.parent) {
          if (typeof o.userData.lineIndex === "number") return o.userData.lineIndex as number;
        }
      }
      return null;
    };
    return () => {
      pickRef.current = null;
    };
  }, [camera, scene, gl, pickRef]);
  return null;
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
  onDropPart,
}: {
  lines: ConceptLine[];
  parts: Map<string, LibraryPart>;
  selected: number | null;
  onSelect: (index: number | null) => void;
  onViewChange: (index: number, view: LineView) => void;
  /** A library part dropped on the view: onto line `target`'s part, or on empty space (null). */
  onDropPart?: (partId: string, option: number, target: number | null) => void;
}) {
  const pickRef = useRef<Pick | null>(null);
  const [dragging, setDragging] = useState(false);
  const [dropTarget, setDropTarget] = useState<number | null>(null);
  const pick = (e: React.DragEvent) => pickRef.current?.(e.clientX, e.clientY) ?? null;
  const accepts = (e: React.DragEvent) => !!onDropPart && e.dataTransfer.types.includes(PART_DRAG_TYPE);
  const endDrag = () => {
    setDragging(false);
    setDropTarget(null);
  };
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
      <div
        className={`sp-3d-drop${dragging ? " sp-3d-dragging" : ""}`}
        onDragOver={(e) => {
          if (!accepts(e)) return;
          e.preventDefault();
          e.dataTransfer.dropEffect = "copy";
          setDragging(true);
          setDropTarget(pick(e));
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) endDrag();
        }}
        onDrop={(e) => {
          if (!accepts(e)) return;
          e.preventDefault();
          const payload = readDragPayload(e.dataTransfer.getData(PART_DRAG_TYPE));
          const target = pick(e);
          endDrag();
          if (payload) onDropPart?.(payload.part_id, payload.option, target);
        }}>
        <ViewerStage observe={false} fitKey={`${lines.length}`} onPointerMissed={() => onSelect(null)} shadowScale={900}
          margin={1.6} className="sp-3d-stage">
          {placed.map((p) => (
            <PlacedPart key={p.index} placed={p} selected={p.index === selected || p.index === dropTarget} materials={materials}
              highlight={highlight} onSelect={onSelect} />
          ))}
          {placed.length === 0 && (
            <Html center className="sp-3d-label">
              {onDropPart ? "Drag parts here from the library" : "Add parts to see them here"}
            </Html>
          )}
          <DropPicker pickRef={pickRef} />
        </ViewerStage>
        {dragging && (
          <div className="sp-drop-hint small">
            {dropTarget !== null && placed[dropTarget]
              ? `Drop to put it on top of ${dropTarget + 1}. ${placed[dropTarget].name}`
              : "Drop to add it to the top of the stack"}
          </div>
        )}
      </div>
      <p className="small muted">
        Drag to orbit, scroll to zoom, right-drag to pan. Click a part to select it.
        {onDropPart && " Drop a library part onto a part to put it on top, or on empty space to add it to the top of the stack."}
      </p>

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
              {sel.made && "Drawn as the part it's made into: its stock becomes this one shape. "}
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
              <label className="sp-view-field">
                <span>Drawn as</span>
                <select value={sel.view.made?.shape ?? ""}
                  onChange={(e) => set({ made: e.target.value ? madeFrom(sel.stock, e.target.value as MadeKind, sel.stockTotal) : null })}>
                  <option value="">Stock, as bought</option>
                  {(Object.keys(MADE_SHAPES) as MadeKind[]).map((k) => (
                    <option key={k} value={k}>Made into a {k}</option>
                  ))}
                </select>
              </label>
              {sel.view.made && MADE_SHAPES[sel.view.made.shape as MadeKind]?.map((key) => (
                <ViewNumber key={key} label={`${MADE_LABELS[key] ?? key} (mm)`} step={1}
                  value={(sel.view.made as unknown as Record<string, number>)[key]}
                  onChange={(v) => set({ made: { ...sel.view.made!, [key]: Math.max(0, v) } as ShapeSpec })} />
              ))}
              {sel.sheetPart && !sel.made && (
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
            {sel.view.made && !sel.made && (
              <p className="small notice">These sizes can&apos;t be drawn (every size above 0, a bore smaller than the outside), so the stock is shown.</p>
            )}
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

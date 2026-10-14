// Standard Parts builder, 3D view: what shape each concept line is drawn as and where it goes. Pure (no three.js),
// so it is tested with npm test; components/ConceptViewer.tsx turns the result into meshes. Units: mm and degrees.
//
// Each part's shape comes from the library's hidden <!-- part-shapes --> block (per price variant). A line's own
// sizes take over where the part is priced by size: a tube's length, a sheet's width × height (or the length or
// share of a sheet worked out from its quantity). Parts without a shape are drawn as labelled placeholder boxes.
// A line is drawn once per piece: its quantity for parts bought by the piece, its count for parts sized in mm (a
// share of a length or sheet is one piece). By default the pieces stack on each other and the lines stack up the
// vertical axis in table order, each on top of the one before; a line's view settings move, turn and repeat it,
// and a line repeated round the centre draws its copies round the centre instead of stacking its pieces. A line can
// also be drawn as the part it is made into (`made`: two blanks glued and turned into one round plinth): then its
// pieces become that one shape.

import type { ConceptLine, LibraryPart } from "./standardParts.ts";

export type ShapeSpec =
  | { shape: "tube"; od: number; id: number; length: number }
  | { shape: "rod"; d: number; length: number }
  | { shape: "bar" | "strip"; width: number; thickness: number; length: number }
  | { shape: "sheet"; width: number; height: number; thickness: number }
  | { shape: "disc"; d: number; thickness: number }
  | { shape: "ring"; od: number; id: number; thickness: number }
  | { shape: "cylinder"; d: number; height: number }
  | { shape: "dome"; d: number; height: number; opening?: number }
  | { shape: "cone"; d_bottom: number; d_top: number; height: number }
  | { shape: "sphere"; d: number }
  | { shape: "globe"; d: number; neck_d: number; neck_height: number }
  | { shape: "box"; width: number; depth: number; height: number };

/** A part's shape as the library gives it (sizes plus an optional colour and a note of what was assumed). */
export type PartShape = ShapeSpec & { look?: string; assumed?: string; source?: string };

export type SheetForm = "auto" | "sheet" | "disc" | "rolled";

/** Where the 3D view puts a line: offsets from its place in the stack, rotation, copies round the axis. */
export interface LineView {
  dx: number; // sideways (left/right), mm
  dy: number; // up/down from its place in the stack, mm
  dz: number; // sideways (front/back), mm
  rx: number; // tilt about the left/right axis, degrees
  ry: number; // turn about the vertical axis, degrees
  rz: number; // tilt about the front/back axis, degrees
  repeat: number; // copies spaced evenly round the vertical axis (at the sideways offset)
  stack: boolean; // whether the next part sits on top of this one (off: it sits inside, like a lampholder in a shade)
  form: SheetForm; // sheet parts: as a flat sheet, cut as a disc, or rolled into a tube
  made: ShapeSpec | null; // drawn as the turned or cut part the line becomes, in place of its stock (null: as bought)
}

export const DEFAULT_VIEW: LineView = {
  dx: 0, dy: 0, dz: 0, rx: 0, ry: 0, rz: 0, repeat: 1, stack: true, form: "auto", made: null,
};

export function viewOf(line: Pick<ConceptLine, "view">): LineView {
  return { ...DEFAULT_VIEW, ...(line.view ?? {}) };
}

/** True when the view is the default, so it needn't be saved. */
export function isDefaultView(v: LineView): boolean {
  return (Object.keys(DEFAULT_VIEW) as (keyof LineView)[]).every((k) => (k === "made" ? !v.made : v[k] === DEFAULT_VIEW[k]));
}

/** Shapes a line can be made into, with their sizes (mm) in the order the builder asks for them. */
export const MADE_SHAPES = {
  cylinder: ["d", "height"],
  disc: ["d", "thickness"],
  ring: ["od", "id", "thickness"],
  tube: ["od", "id", "length"],
  rod: ["d", "length"],
  box: ["width", "depth", "height"],
  cone: ["d_bottom", "d_top", "height"],
  dome: ["d", "height"],
  sphere: ["d"],
} as const;
export type MadeKind = keyof typeof MADE_SHAPES;

/** Sizes that may be zero (a solid tube or ring, a cone to a point); every other size must be positive. */
const ZERO_OK = new Set(["id", "d_top"]);

/** A made shape the 3D view can draw: known kind, every size a number in range, a bore smaller than the outside. */
export function validMade(s: unknown): s is ShapeSpec {
  if (!s || typeof s !== "object") return false;
  const o = s as Record<string, unknown>;
  const keys = MADE_SHAPES[o.shape as MadeKind];
  if (!keys) return false;
  const ok = keys.every((k) => typeof o[k] === "number" && (o[k] as number) >= 0 && (ZERO_OK.has(k) || (o[k] as number) > 0));
  return ok && !("od" in o && (o.id as number) >= (o.od as number));
}

/**
 * A starting size for making a line into `kind`: as wide as its stock (a box's narrower side, so a square blank
 * turns to the round it can give) and as tall as its stacked pieces.
 */
export function madeFrom(stock: ShapeSpec | null, kind: MadeKind, total: number): ShapeSpec {
  const d = +(!stock ? PLACEHOLDER_SIZE : stock.shape === "box" ? Math.min(stock.width, stock.depth) : 2 * shapeRadius(stock)).toFixed(1);
  const h = +Math.max(total, 1).toFixed(2);
  switch (kind) {
    case "cylinder": return { shape: "cylinder", d, height: h };
    case "disc": return { shape: "disc", d, thickness: h };
    case "ring": return { shape: "ring", od: d, id: +(d / 2).toFixed(1), thickness: h };
    case "tube": return { shape: "tube", od: d, id: +(d * 0.8).toFixed(1), length: h };
    case "rod": return { shape: "rod", d, length: h };
    case "box": return { shape: "box", width: d, depth: d, height: h };
    case "cone": return { shape: "cone", d_bottom: d, d_top: +(d / 2).toFixed(1), height: h };
    case "dome": return { shape: "dome", d, height: h };
    case "sphere": return { shape: "sphere", d };
  }
}

export const PLACEHOLDER_SIZE = 40;
/** Most pieces drawn for one line (a line of 500 screws would otherwise be a tower). */
export const MAX_PIECES = 24;

/** How many pieces a line is drawn as: its count of sized pieces, or its quantity of whole parts. */
export function linePieces(line: ConceptLine, part: Pick<LibraryPart, "units"> | undefined): number {
  const sized = line.length_mm != null || line.width_mm != null || line.height_mm != null;
  const clamp = (n: number) => Math.min(MAX_PIECES, Math.max(1, Math.round(n)));
  if (sized) return clamp(line.count ?? 1);
  if (part && unitOf(part, line.option)) return 1; // a share of a priced length or sheet
  return line.quantity >= 1 ? clamp(line.quantity) : 1;
}

/** Height of a shape as drawn upright (tubes, rods and bars stand on end; sheets and discs lie flat). */
export function shapeHeight(s: ShapeSpec): number {
  switch (s.shape) {
    case "tube":
    case "rod":
    case "bar":
    case "strip":
      return s.length;
    case "sheet":
    case "disc":
    case "ring":
      return s.thickness;
    case "cylinder":
    case "dome":
    case "cone":
    case "box":
      return s.height;
    case "sphere":
      return s.d;
    case "globe":
      return globeGeometry(s).height;
  }
}

/** A globe on its neck: the neck rises from 0, the sphere meets its rim. */
export function globeGeometry(s: { d: number; neck_d: number; neck_height: number }) {
  const r = s.d / 2;
  const nr = Math.min(s.neck_d / 2, r * 0.98);
  const centre = s.neck_height + Math.sqrt(r * r - nr * nr);
  return { r, nr, centre, height: centre + r, openAngle: Math.PI - Math.asin(nr / r) };
}

/** Widest extent of a shape round the axis (for spacing copies and sizing placeholders). */
export function shapeRadius(s: ShapeSpec): number {
  switch (s.shape) {
    case "tube":
    case "ring":
      return s.od / 2;
    case "rod":
    case "disc":
    case "cylinder":
    case "dome":
    case "sphere":
    case "globe":
      return s.d / 2;
    case "cone":
      return Math.max(s.d_bottom, s.d_top) / 2;
    case "bar":
    case "strip":
      return Math.hypot(s.width, s.thickness) / 2;
    case "sheet":
      return Math.hypot(s.width, s.height) / 2;
    case "box":
      return Math.hypot(s.width, s.depth) / 2;
  }
}

export function partShape(part: Pick<LibraryPart, "shapes"> | undefined, option: number): PartShape | null {
  const shapes = part?.shapes;
  if (!shapes?.length) return null;
  return (shapes[Math.min(Math.max(option, 0), shapes.length - 1)] as PartShape | null) ?? null;
}

function unitOf(part: Pick<LibraryPart, "units">, option: number) {
  const units = part.units;
  if (!units?.length) return null;
  return units[Math.min(Math.max(option, 0), units.length - 1)] ?? null;
}

/**
 * The shape drawn for a line: the part's shape with the line's own sizes, and a sheet cut or rolled as the
 * view asks. A length-priced part takes the line's length (or its share of the priced length); a sheet-priced
 * part takes the line's width × height (or a square of its share of the sheet).
 */
export function lineShape(line: ConceptLine, part: Pick<LibraryPart, "shapes" | "units"> | undefined): ShapeSpec | null {
  const made = viewOf(line).made;
  if (validMade(made)) return made;
  return stockShape(line, part);
}

/** The shape of the stock as bought (ignoring what the line is made into). */
export function stockShape(line: ConceptLine, part: Pick<LibraryPart, "shapes" | "units"> | undefined): ShapeSpec | null {
  const base = partShape(part, line.option);
  if (!base || !part) return null;
  const { look: _look, assumed: _assumed, source: _source, ...shape } = base;
  let spec = { ...shape } as ShapeSpec;
  const unit = unitOf(part, line.option);
  if (unit && "length_mm" in unit && "length" in spec) {
    const length = line.length_mm ?? line.quantity * unit.length_mm;
    if (length > 0) spec = { ...spec, length } as ShapeSpec;
  }
  if (unit && "width_mm" in unit && spec.shape === "sheet") {
    let width = line.width_mm ?? 0;
    let height = line.height_mm ?? 0;
    if (line.width_mm == null && line.height_mm == null) {
      width = height = Math.sqrt(Math.max(line.quantity, 0) * unit.width_mm * unit.height_mm);
    }
    if (width > 0 && height > 0) spec = { ...spec, width, height };
  }
  if (spec.shape === "sheet") {
    const { width, height, thickness } = spec;
    const form = viewOf(line).form;
    if (form === "disc") return { shape: "disc", d: Math.min(width, height), thickness };
    if (form === "rolled") {
      const od = width / Math.PI; // the sheet's width becomes the tube's circumference
      return { shape: "tube", od, id: Math.max(od - 2 * thickness, 0), length: height };
    }
  }
  return spec;
}

/** One copy of a line's part: its angle round the vertical axis (degrees). */
export interface Instance {
  angle: number;
}

export interface Placed {
  index: number; // the line's row in the parts table
  name: string;
  spec: ShapeSpec | null; // null: a placeholder box
  look: string;
  assumed: string;
  height: number; // one piece
  pieces: number; // pieces stacked on each other (1 when the line repeats round the centre)
  total: number; // height of the stacked pieces: what the line adds to the stack
  base: number; // where its place in the stack starts (before its own up/down offset)
  view: LineView;
  instances: Instance[];
  sheetPart: boolean; // priced as a sheet, so it can be cut as a disc or rolled
  made: boolean; // drawn as the part it's made into, not its stock
  stock: ShapeSpec | null; // the stock as bought
  stockTotal: number; // height of the stock's stacked pieces (a starting height for a made shape)
}

/** Every line placed: stacked bottom-up in table order, each sitting on the one before unless it is set not to. */
export function layoutConcept(lines: ConceptLine[], parts: Map<string, LibraryPart>): Placed[] {
  let level = 0;
  return lines.map((line, index) => {
    const part = parts.get(line.part_id);
    const spec = lineShape(line, part);
    const view = viewOf(line);
    const height = spec ? shapeHeight(spec) : PLACEHOLDER_SIZE;
    const repeat = Math.max(1, Math.round(view.repeat));
    const made = validMade(view.made);
    const stockPieces = repeat > 1 ? 1 : linePieces(line, part);
    const pieces = made ? 1 : stockPieces;
    const stock = made ? stockShape(line, part) : spec;
    const total = height * pieces;
    const base = level;
    if (view.stack) level += total;
    const shape = partShape(part, line.option);
    const unit = part ? unitOf(part, line.option) : null;
    return {
      index,
      name: part?.name ?? line.part_id,
      spec,
      look: shape?.look ?? part?.look ?? "other",
      assumed: made ? "" : (shape?.assumed ?? ""),
      height,
      pieces,
      total,
      base,
      view,
      instances: Array.from({ length: repeat }, (_, k) => ({ angle: (360 * k) / repeat })),
      sheetPart: !!unit && "width_mm" in unit && shape?.shape === "sheet",
      made,
      stock,
      stockTotal: (stock ? shapeHeight(stock) : PLACEHOLDER_SIZE) * stockPieces,
    };
  });
}

const mmText = (v: number) => `${+v.toFixed(1)}`;

/** "tube Ø80 × 210 mm, Ø74 bore": a shape's sizes in words, for the library preview. */
export function describeShape(s: ShapeSpec): string {
  switch (s.shape) {
    case "tube":
      return `tube Ø${mmText(s.od)} × ${mmText(s.length)} mm${s.id > 0 ? `, Ø${mmText(s.id)} bore` : ""}`;
    case "rod":
      return `rod Ø${mmText(s.d)} × ${mmText(s.length)} mm`;
    case "bar":
    case "strip":
      return `${s.shape} ${mmText(s.width)} × ${mmText(s.thickness)} × ${mmText(s.length)} mm`;
    case "sheet":
      return `sheet ${mmText(s.width)} × ${mmText(s.height)} × ${mmText(s.thickness)} mm`;
    case "disc":
      return `disc Ø${mmText(s.d)} × ${mmText(s.thickness)} mm`;
    case "ring":
      return `ring Ø${mmText(s.od)} × ${mmText(s.thickness)} mm${s.id > 0 ? `, Ø${mmText(s.id)} bore` : ""}`;
    case "cylinder":
      return `cylinder Ø${mmText(s.d)} × ${mmText(s.height)} mm`;
    case "dome":
      return `dome Ø${mmText(s.d)} × ${mmText(s.height)} mm${s.opening ? `, Ø${mmText(s.opening)} opening` : ""}`;
    case "cone":
      return `cone Ø${mmText(s.d_bottom)} to Ø${mmText(s.d_top)} × ${mmText(s.height)} mm`;
    case "sphere":
      return `sphere Ø${mmText(s.d)}`;
    case "globe":
      return `globe Ø${mmText(s.d)} on a Ø${mmText(s.neck_d)} × ${mmText(s.neck_height)} mm neck`;
    case "box":
      return `box ${mmText(s.width)} × ${mmText(s.depth)} × ${mmText(s.height)} mm`;
  }
}

/**
 * A part dropped into the 3D view. On empty space (`target` null) it goes at the end of the table, so it sits on
 * top of the stack. On a part it goes in the row after that part, sitting on its top: in a part that stacks, it
 * joins the stack there (whatever was above moves up by its height) and keeps the part's sideways offset; on a part
 * that doesn't stack (a lampholder inside a shade) or one repeated round the centre (feet), it sits on the part's
 * top without moving anything else, one on each copy. The part's tilt isn't followed.
 */
export function insertOnTop(lines: ConceptLine[], placed: Placed[], target: number | null, line: ConceptLine) {
  const p = target !== null ? placed[target] : undefined;
  if (!p) return { lines: [...lines, line], index: lines.length };
  const v = p.view;
  const view: Partial<LineView> = {};
  if (v.dx) view.dx = v.dx;
  if (v.dz) view.dz = v.dz;
  if (v.stack && v.repeat <= 1) {
    if (v.dy) view.dy = v.dy; // the next level is the part's top before its own offset
  } else {
    if (v.repeat > 1) view.repeat = v.repeat;
    view.stack = false;
    const base = p.base + (v.stack ? p.total : 0); // where the new row's place in the stack starts
    const dy = p.base + v.dy + p.total - base;
    if (dy) view.dy = +dy.toFixed(3);
  }
  const added: ConceptLine = Object.keys(view).length ? { ...line, view } : line;
  const index = p.index + 1;
  return { lines: [...lines.slice(0, index), added, ...lines.slice(index)], index };
}

/** Drag-and-drop from the library panel into the 3D view: the data type and its payload (part id and variant). */
export const PART_DRAG_TYPE = "application/x-bathsheva-part";

export function dragPayload(partId: string, option: number): string {
  return JSON.stringify({ part_id: partId, option });
}

export function readDragPayload(raw: string): { part_id: string; option: number } | null {
  try {
    const v = JSON.parse(raw) as { part_id?: unknown; option?: unknown };
    if (typeof v.part_id !== "string" || !v.part_id) return null;
    return { part_id: v.part_id, option: Number.isInteger(v.option) && (v.option as number) >= 0 ? (v.option as number) : 0 };
  } catch {
    return null;
  }
}

// Run with: npm test (node --test, Node 22.6+ strips the types).
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_VIEW, globeGeometry, isDefaultView, layoutConcept, linePieces, lineShape, madeFrom, MAX_PIECES, PLACEHOLDER_SIZE, shapeHeight,
  validMade, viewOf,
} from "./conceptShapes.ts";
import { plainLines, type ConceptLine, type LibraryPart } from "./standardParts.ts";

const part = (id: string, extra: Partial<LibraryPart>) => ({ id, name: id, units: [], shapes: [], look: "other", ...extra }) as unknown as LibraryPart;
const line = (part_id: string, extra: Partial<ConceptLine> = {}): ConceptLine => ({ part_id, quantity: 1, note: "", option: 0, ...extra });

const TUBE = part("tube", { units: [{ length_mm: 2500 }], shapes: [{ shape: "tube", od: 12.7, id: 9.44, length: 2500 }], look: "brass" });
const PLY = part("ply", { units: [{ width_mm: 2440, height_mm: 1220 }], shapes: [{ shape: "sheet", width: 2440, height: 1220, thickness: 18 }], look: "wood" });
const RING = part("ring", { shapes: [{ shape: "ring", od: 48, id: 37, thickness: 3.5 }], look: "brass" });
const GLOBE = part("globe", { shapes: [{ shape: "globe", d: 150, neck_d: 80, neck_height: 25, assumed: "neck 25 mm high" }], look: "glass_opal" });
const KIT = part("kit", {});
const BLANK = part("blank", { shapes: [{ shape: "box", width: 101.6, depth: 101.6, height: 44.45 }], look: "wood" });
const SHEET2 = part("sheet2", {
  units: [{ width_mm: 45, height_mm: 45 }, { width_mm: 250, height_mm: 250 }],
  shapes: [{ shape: "sheet", width: 45, height: 45, thickness: 0.9 }, { shape: "sheet", width: 250, height: 250, thickness: 0.9 }],
});
const PARTS = new Map([TUBE, PLY, RING, GLOBE, KIT, SHEET2, BLANK].map((p) => [p.id, p]));

test("a tube takes the line's length, or its share of the priced length", () => {
  assert.deepEqual(lineShape(line("tube", { length_mm: 300 }), TUBE), { shape: "tube", od: 12.7, id: 9.44, length: 300 });
  assert.equal((lineShape(line("tube", { quantity: 0.072 }), TUBE) as { length: number }).length, 180);
});

test("a sheet takes the line's width × height, or a square of its share", () => {
  assert.deepEqual(lineShape(line("ply", { width_mm: 160, height_mm: 200 }), PLY), { shape: "sheet", width: 160, height: 200, thickness: 18 });
  const sq = lineShape(line("ply", { quantity: 0.01 }), PLY) as { width: number; height: number };
  assert.ok(Math.abs(sq.width * sq.height - 0.01 * 2440 * 1220) < 1e-6);
});

test("a sheet can be drawn as a cut disc or rolled into a tube", () => {
  const disc = lineShape(line("ply", { width_mm: 160, height_mm: 160, view: { form: "disc" } }), PLY);
  assert.deepEqual(disc, { shape: "disc", d: 160, thickness: 18 });
  const rolled = lineShape(line("ply", { width_mm: 377, height_mm: 250, view: { form: "rolled" } }), PLY) as { od: number; length: number };
  assert.ok(Math.abs(rolled.od - 377 / Math.PI) < 1e-9 && rolled.length === 250);
});

test("the shape follows the price variant", () => {
  const big = lineShape(line("sheet2", { option: 1, width_mm: 100, height_mm: 100 }), SHEET2) as { thickness: number; width: number };
  assert.equal(big.width, 100);
  assert.deepEqual(lineShape(line("sheet2", { option: 0 }), SHEET2), { shape: "sheet", width: 45, height: 45, thickness: 0.9 });
});

test("parts stack up the axis in table order; a part set not to stack doesn't raise the next", () => {
  const lines = [line("ring"), line("tube", { length_mm: 200 }), line("kit"), line("ring", { view: { stack: false } }), line("ring")];
  const placed = layoutConcept(lines, PARTS);
  assert.deepEqual(placed.map((p) => p.base), [0, 3.5, 203.5, 203.5 + PLACEHOLDER_SIZE, 203.5 + PLACEHOLDER_SIZE]);
  assert.equal(placed[2].spec, null); // no shape: a placeholder
  assert.equal(placed[2].height, PLACEHOLDER_SIZE);
  assert.equal(placed[1].look, "brass");
});

test("repeats are spaced evenly round the centre", () => {
  const [feet] = layoutConcept([line("ring", { view: { repeat: 3, dx: 40 } })], PARTS);
  assert.deepEqual(feet.instances.map((i) => i.angle), [0, 120, 240]);
  assert.equal(feet.view.dx, 40);
});

test("assumed sizes are reported; the globe sits on its neck", () => {
  const [g] = layoutConcept([line("globe")], PARTS);
  assert.equal(g.assumed, "neck 25 mm high");
  const geo = globeGeometry({ d: 150, neck_d: 80, neck_height: 25 });
  assert.equal(shapeHeight({ shape: "globe", d: 150, neck_d: 80, neck_height: 25 }), geo.height);
  assert.ok(Math.abs(geo.centre - (25 + Math.sqrt(75 ** 2 - 40 ** 2))) < 1e-9);
});

test("unknown parts are placeholders, and a line's view is saved only when it isn't the default", () => {
  assert.equal(layoutConcept([line("gone")], PARTS)[0].spec, null);
  assert.deepEqual(viewOf(line("ring")), DEFAULT_VIEW);
  assert.equal(plainLines([line("ring", { view: { ...DEFAULT_VIEW } })])[0].view, undefined);
  assert.deepEqual(plainLines([line("ring", { view: { dy: 5 } })])[0].view, { ...DEFAULT_VIEW, dy: 5 });
});

test("a line is drawn once per unit, its pieces stacked; a share of a length or sheet is one piece", () => {
  assert.equal(linePieces(line("ring", { quantity: 2 }), RING), 2);
  assert.equal(linePieces(line("ply", { width_mm: 160, height_mm: 160, count: 3 }), PLY), 3);
  assert.equal(linePieces(line("ply", { quantity: 0.05 }), PLY), 1);
  assert.equal(linePieces(line("tube", { quantity: 2 }), TUBE), 1); // two priced lengths drawn as one 5 m tube
  assert.equal(linePieces(line("kit", { quantity: 0.5 }), KIT), 1);
  assert.equal(linePieces(line("kit", { quantity: 500 }), KIT), MAX_PIECES);
  const placed = layoutConcept([line("ring", { quantity: 2 }), line("ring")], PARTS);
  assert.equal(placed[0].pieces, 2);
  assert.equal(placed[0].total, 7);
  assert.equal(placed[1].base, 7);
});

test("a line repeated round the centre draws one piece per copy instead of stacking", () => {
  const placed = layoutConcept([line("ring", { quantity: 3, view: { repeat: 3, dx: 40 } }), line("ring")], PARTS);
  assert.equal(placed[0].pieces, 1);
  assert.equal(placed[0].instances.length, 3);
  assert.equal(placed[1].base, 3.5);
});

test("a line can be drawn as the part it's made into: two blanks turned into one round plinth", () => {
  const plinth = { shape: "cylinder", d: 100, height: 88.9 } as const;
  const placed = layoutConcept([line("blank", { quantity: 2, view: { made: plinth } }), line("ring")], PARTS);
  assert.deepEqual(placed[0].spec, plinth);
  assert.equal(placed[0].pieces, 1);
  assert.equal(placed[0].made, true);
  assert.equal(placed[0].look, "wood");
  assert.equal(placed[1].base, 88.9);
  // Its starting size: as wide as the square blank, as tall as the two stacked.
  const stock = layoutConcept([line("blank", { quantity: 2 })], PARTS)[0];
  assert.equal(stock.total, 88.9);
  assert.deepEqual(madeFrom(stock.spec, "cylinder", stock.total), { shape: "cylinder", d: 101.6, height: 88.9 });
  assert.equal(isDefaultView({ ...DEFAULT_VIEW, made: null }), true);
  assert.equal(isDefaultView({ ...DEFAULT_VIEW, made: plinth }), false);
});

test("a made shape that can't be drawn falls back to the stock", () => {
  assert.equal(validMade({ shape: "ring", od: 10, id: 12, thickness: 2 }), false);
  assert.equal(validMade({ shape: "cylinder", d: 0, height: 5 }), false);
  assert.equal(validMade({ shape: "cone", d_bottom: 50, d_top: 0, height: 20 }), true);
  const [p] = layoutConcept([line("blank", { quantity: 2, view: { made: { shape: "cylinder", d: 0, height: 5 } } })], PARTS);
  assert.equal(p.made, false);
  assert.equal(p.pieces, 2);
});

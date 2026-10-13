// Run with: npm test (node --test, Node 22.6+ strips the types).
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  newLine,
  sizeLabel,
  toQuantity,
  toSizes,
  unitFor,
  unitLabel,
  extraPriceText,
  factoryTarget,
  inlineSegments,
  matchesSearch,
  noPriceLabel,
  plainLines,
  priceLabel,
  sentence,
  type LibraryPart,
} from "./standardParts.ts";

const part = {
  name: "Internally frosted cylinder shade",
  material: "Borosilicate",
  sizes: "80 mm Ø × 210 mm",
  supplier: "J Moncrieff, UK",
  category: "1. Tubes",
  subcategory: "1.5 Glass tube — borosilicate",
} as LibraryPart;

test("search matches every word across name, supplier and category", () => {
  assert.ok(matchesSearch(part, "frosted moncrieff"));
  assert.ok(matchesSearch(part, "  "));
  assert.ok(matchesSearch(part, "TUBES"));
  assert.ok(!matchesSearch(part, "frosted brass"));
});

test("parts without a price are labelled as in the library", () => {
  assert.equal(noPriceLabel({ price_status: "quote" }), "Quote only");
  assert.equal(noPriceLabel({ price_status: "not_shown" }), "Price not shown");
  assert.equal(noPriceLabel({ price_status: "listed" }), null);
});

test("factory target is a share of the ex-VAT retail price", () => {
  const pricing = { vat_rate: 0.2, dtc_factory_share: 0.33 };
  assert.equal(factoryTarget(240, pricing)?.toFixed(2), "66.00");
  assert.equal(factoryTarget(null, pricing), null);
  assert.equal(factoryTarget(0, pricing), null);
});

test("foreign prices show the converted figure", () => {
  assert.equal(priceLabel({ price: 4.99, currency: "GBP", label: "", price_gbp: 4.99 }), "£4.99");
  assert.equal(priceLabel({ price: 12.56, currency: "EUR", label: "", price_gbp: 10.676 }), "€12.56 (≈ £10.68)");
});

test("inline markdown: bold, code and links", () => {
  assert.deepEqual(inlineSegments("See **Note:** [link](https://x.uk/a) and `id`."), [
    { kind: "text", text: "See " },
    { kind: "bold", text: "Note:" },
    { kind: "text", text: " " },
    { kind: "link", text: "link", url: "https://x.uk/a" },
    { kind: "text", text: " and " },
    { kind: "code", text: "id" },
    { kind: "text", text: "." },
  ]);
  assert.deepEqual(inlineSegments("plain"), [{ kind: "text", text: "plain" }]);
});

test("lines sent to the API keep only their own fields", () => {
  const costed = { part_id: "a", quantity: 2, note: "n", option: 1, cost_100: 3, known: true };
  assert.deepEqual(plainLines([costed]), [{ part_id: "a", quantity: 2, note: "n", option: 1 }]);
});

test("price text is repeated only when it adds something", () => {
  const opt = { price: 9.86, currency: "GBP", label: "", price_gbp: 9.86 };
  assert.equal(extraPriceText({ price_text: "£9.86", options: [opt] }), null);
  assert.equal(extraPriceText({ price_text: "£9.86 per pack of 10", options: [opt] }), "£9.86 per pack of 10");
  assert.equal(sentence("supply at volume."), "Supply at volume.");
});

test("sizes in mm: labels, new lines and the priced unit per variant", () => {
  assert.equal(unitLabel({ length_mm: 2500 }), "2.5 m length");
  assert.equal(unitLabel({ length_mm: 304.8 }), "304.8 mm length");
  assert.equal(unitLabel({ width_mm: 250, height_mm: 250 }), "250 × 250 mm sheet");
  const sheet = { id: "s", units: [{ width_mm: 45, height_mm: 45 }, { width_mm: 250, height_mm: 250 }] };
  assert.deepEqual(unitFor(sheet, 1), { width_mm: 250, height_mm: 250 });
  assert.equal(unitFor({ units: [] }, 0), null);
  assert.deepEqual(newLine({ id: "t", units: [{ length_mm: 2500 }] }), { part_id: "t", quantity: 1, note: "", option: 0, length_mm: 100, count: 1 });
  assert.deepEqual(newLine({ id: "k", units: [] }), { part_id: "k", quantity: 1, note: "", option: 0 });
  assert.equal(sizeLabel({ part_id: "p", quantity: 0, note: "", option: 0, width_mm: 160, height_mm: 160, count: 3, waste_pct: 30 }), "3 × 160 × 160 mm + 30% waste");
  assert.equal(sizeLabel({ part_id: "p", quantity: 0.12, note: "", option: 0, length_mm: 300, count: 1 }), "300 mm");
  assert.equal(sizeLabel({ part_id: "p", quantity: 2, note: "", option: 0 }), "");
});

test("switching between a share and mm keeps the same quantity", () => {
  const line = { part_id: "t", quantity: 0.12, note: "stem", option: 0 };
  const byLength = toSizes(line, { length_mm: 2500 });
  assert.equal(byLength.length_mm, 300);
  const bySheet = toSizes({ ...line, quantity: 0.16 }, { width_mm: 250, height_mm: 250 });
  assert.equal(bySheet.width_mm, 100);
  assert.equal(bySheet.height_mm, 100);
  assert.deepEqual(toQuantity(byLength, 0.12), line);
});

test("lines sent to the API keep their sizes", () => {
  const sized = { part_id: "t", quantity: 0.12, note: "", option: 0, length_mm: 300, count: 2, width_mm: null };
  assert.deepEqual(plainLines([sized]), [{ part_id: "t", quantity: 0.12, note: "", option: 0, length_mm: 300, count: 2 }]);
});

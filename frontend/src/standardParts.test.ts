// Run with: npm test (node --test, Node 22.6+ strips the types).
import { test } from "node:test";
import assert from "node:assert/strict";
import {
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

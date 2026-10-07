// Run with: npm test (node --test, Node 22.6+ strips the types).
import { test } from "node:test";
import assert from "node:assert/strict";
import { ukDateTime } from "./format.ts";

test("summer times are shown in BST (UTC+1)", () => {
  assert.equal(ukDateTime("2026-10-06T13:52:00Z"), "06/10/2026 14:52");
  assert.equal(ukDateTime("2026-10-06T13:52:00+00:00"), "06/10/2026 14:52");
});

test("winter times are shown in GMT", () => {
  assert.equal(ukDateTime("2026-12-01T09:05:00Z"), "01/12/2026 09:05");
});

test("timestamps without a zone are UTC", () => {
  assert.equal(ukDateTime("2026-10-07T08:05:00"), "07/10/2026 09:05");
});

test("midnight uses the 24-hour clock", () => {
  assert.equal(ukDateTime("2026-10-06T23:00:00Z"), "07/10/2026 00:00");
});

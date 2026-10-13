// Standard Parts page: API types and pure helpers (tested with npm test).

import { DEFAULT_VIEW, isDefaultView, type LineView, type PartShape } from "./conceptShapes.ts";

export interface PriceOption {
  price: number;
  currency: string;
  label: string;
  price_gbp: number;
}

export interface LibraryPart {
  id: string;
  category: string;
  subcategory: string;
  name: string;
  material: string;
  sizes: string;
  supplier: string;
  supplier_cell: string;
  links: { label: string; url: string }[];
  /** Repo files the entry comes from instead of a web page (a supplier's price list export). */
  source_files: string[];
  price_text: string;
  price_status: "listed" | "quote" | "not_shown";
  price: number | null;
  currency: string | null;
  price_gbp: number | null;
  options: PriceOption[];
  price_from: boolean;
  price_uncertain: boolean;
  breaks_text: string;
  breaks: { quantity: number; price: number; currency: string; price_gbp: number }[];
  moq: string;
  note: string;
  availability: string;
  /** Per price variant: the priced unit in mm (a length or a sheet), or null for a piece or pack. */
  units: (PricedUnit | null)[];
  /** Per price variant: how the 3D view draws it, or null for a labelled placeholder. */
  shapes: (PartShape | null)[];
  /** Material colour for the 3D view (brass, glass, wood, ...). */
  look: string;
}

export type PricedUnit = { length_mm: number } | { width_mm: number; height_mm: number };

export interface LibrarySubsection {
  number: string;
  title: string;
  notes: string[];
  parts: LibraryPart[];
}

export interface Library {
  sections: { number: string; title: string; subsections: LibrarySubsection[] }[];
  about: { title: string; lines: string[] }[];
  /** Old part id -> current id, for parts whose name or supplier was corrected. */
  aliases: Record<string, string>;
  fx: Record<string, number>;
  quantities: number[];
  room_share: number;
  pricing: { vat_rate: number; dtc_factory_share: number };
}

export interface ConceptLine {
  part_id: string;
  /** In the part's priced unit (0.12 of a 2.5 m length). The server works it out when sizes are given. */
  quantity: number;
  note: string;
  option: number;
  /** Sizes in mm for parts priced by length or by sheet; they replace `quantity`. */
  length_mm?: number | null;
  width_mm?: number | null;
  height_mm?: number | null;
  count?: number | null;
  waste_pct?: number | null;
  /** Placement in the builder's 3D view (offsets, rotation, repeat); absent means the default. */
  view?: Partial<LineView> | null;
}

const SIZE_KEYS = ["length_mm", "width_mm", "height_mm", "count", "waste_pct"] as const;

export type Verdict = "room" | "tight" | "over";

export interface CostLine extends ConceptLine {
  mode: "units" | "length" | "area";
  size_problem: string;
  unit_size: PricedUnit | null;
  known: boolean;
  priced: boolean;
  unit_100: number | null;
  cost_100: number;
  break_100: boolean;
  unit_500: number | null;
  cost_500: number;
  break_500: boolean;
}

export interface ConceptCost {
  lines: CostLine[];
  retail_price: number | null;
  target: number | null;
  unpriced: string[];
  unknown: string[];
  total_100: number;
  total_500: number;
  share_100: number | null;
  share_500: number | null;
  verdict_100: Verdict | null;
  verdict_500: Verdict | null;
}

export interface SeedConcept {
  number: number;
  key: string;
  name: string;
  subtitle: string;
  group: string;
  description: string;
  retail_price: number | null;
  library_parts: string[];
  custom_work: string;
  parts_cost_text: string;
  stated_cost: Record<string, number>;
  not_in_library: string;
  main_risk: string;
  lines: ConceptLine[];
  cost: ConceptCost;
}

export interface SavedConcept {
  id: number;
  name: string;
  retail_price: number | null;
  based_on: string | null;
  lines: ConceptLine[];
  notes: string;
  created_at: string;
  updated_at: string;
  cost: ConceptCost;
}

export const QUANTITIES = [100, 500] as const;

export const gbp = (v: number) => `£${v.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** "£4.99", "€12.56 (≈ £10.68)" for a price option. */
export function priceLabel(o: PriceOption): string {
  const sym = o.currency === "GBP" ? "£" : o.currency === "EUR" ? "€" : "$";
  const base = `${sym}${o.price.toFixed(2)}`;
  return o.currency === "GBP" ? base : `${base} (≈ ${gbp(o.price_gbp)})`;
}

/** Badge text for a part with no listed price, as the library words it. */
export function noPriceLabel(p: Pick<LibraryPart, "price_status">): string | null {
  if (p.price_status === "quote") return "Quote only";
  if (p.price_status === "not_shown") return "Price not shown";
  return null;
}

export const VERDICT_LABEL: Record<Verdict, string> = { room: "Room", tight: "Tight", over: "Over" };
export const VERDICT_TILE: Record<Verdict, string> = { room: "pass", tight: "warning", over: "fail" };

/** Factory-cost target: ex-VAT retail × the DTC factory share. */
export function factoryTarget(retail: number | null, pricing: Library["pricing"]): number | null {
  if (!retail || retail <= 0) return null;
  return (retail / (1 + pricing.vat_rate)) * pricing.dtc_factory_share;
}

export function allParts(lib: Library): LibraryPart[] {
  return lib.sections.flatMap((s) => s.subsections.flatMap((sub) => sub.parts));
}

/** Every word of the query appears in the part's name, material, sizes, supplier or category. */
export function matchesSearch(p: LibraryPart, query: string): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  const hay = [p.name, p.material, p.sizes, p.supplier, p.category, p.subcategory].join(" ").toLowerCase();
  return words.every((w) => hay.includes(w));
}

export type Segment =
  | { kind: "text"; text: string }
  | { kind: "bold"; text: string }
  | { kind: "code"; text: string }
  | { kind: "link"; text: string; url: string };

/** Inline markdown as used in standard-parts/*.md: **bold**, `code` and [links](url). */
export function inlineSegments(text: string): Segment[] {
  const out: Segment[] = [];
  const re = /\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)/g;
  let last = 0;
  for (let m = re.exec(text); m; m = re.exec(text)) {
    if (m.index > last) out.push({ kind: "text", text: text.slice(last, m.index) });
    if (m[1] !== undefined) out.push({ kind: "bold", text: m[1] });
    else if (m[2] !== undefined) out.push({ kind: "code", text: m[2] });
    else out.push({ kind: "link", text: m[3], url: m[4] });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

/** First letter upper-cased ("supply at volume." → "Supply at volume."). */
export function sentence(text: string): string {
  return text ? text[0].toUpperCase() + text.slice(1) : text;
}

/** The raw price text, when it says more than the headline figure (pack size, VAT basis, variants). */
export function extraPriceText(p: Pick<LibraryPart, "price_text" | "options">): string | null {
  const t = p.price_text.trim();
  return p.options.length === 1 && t === priceLabel(p.options[0]) ? null : t;
}

/** Concept lines as sent to the API, dropping fields the server adds and sizes that aren't set. */
export function plainLines(lines: ConceptLine[]): ConceptLine[] {
  return lines.map((l) => {
    const out: ConceptLine = { part_id: l.part_id, quantity: l.quantity, note: l.note, option: l.option };
    for (const k of SIZE_KEYS) if (l[k] !== undefined && l[k] !== null) out[k] = l[k];
    if (l.view && !isDefaultView({ ...DEFAULT_VIEW, ...l.view })) out.view = { ...DEFAULT_VIEW, ...l.view };
    return out;
  });
}

// ---------------------------------------------------------------------------
// Sizes in mm
// ---------------------------------------------------------------------------

export function unitFor(part: Pick<LibraryPart, "units">, option: number): PricedUnit | null {
  if (!part.units?.length) return null;
  return part.units[Math.min(Math.max(option, 0), part.units.length - 1)] ?? null;
}

export const isLength = (u: PricedUnit | null): u is { length_mm: number } => !!u && "length_mm" in u;
export const isSheet = (u: PricedUnit | null): u is { width_mm: number; height_mm: number } => !!u && "width_mm" in u;

const mm = (v: number) => `${+v.toFixed(1)}`;

/** "2.5 m length", "304.8 mm length", "250 × 250 mm sheet". */
export function unitLabel(u: PricedUnit): string {
  if (isLength(u)) return u.length_mm >= 1000 && u.length_mm % 100 === 0 ? `${u.length_mm / 1000} m length` : `${mm(u.length_mm)} mm length`;
  return `${mm(u.width_mm)} × ${mm(u.height_mm)} mm sheet`;
}

export function hasSizes(l: ConceptLine): boolean {
  return l.length_mm != null || l.width_mm != null || l.height_mm != null;
}

/** "2 × 300 mm", "3 × 160 × 160 mm + 30% waste", or "" when the line is a plain quantity. */
export function sizeLabel(l: ConceptLine): string {
  if (!hasSizes(l)) return "";
  const count = l.count ?? 1;
  const size = l.length_mm != null ? `${mm(l.length_mm)} mm` : `${mm(l.width_mm ?? 0)} × ${mm(l.height_mm ?? 0)} mm`;
  const waste = l.waste_pct ? ` + ${+l.waste_pct.toFixed(1)}% waste` : "";
  return `${count === 1 ? "" : `${+count.toFixed(3)} × `}${size}${waste}`;
}

/** A new line for a part: sized in mm (100 mm, or 100 × 100 mm) when the part is priced by size, else 1 unit. */
export function newLine(part: Pick<LibraryPart, "id" | "units">): ConceptLine {
  const u = unitFor(part, 0);
  const base = { part_id: part.id, quantity: 1, note: "", option: 0 };
  if (isLength(u)) return { ...base, length_mm: 100, count: 1 };
  if (isSheet(u)) return { ...base, width_mm: 100, height_mm: 100, count: 1, waste_pct: 0 };
  return base;
}

/** Restate a fraction as sizes giving exactly the same quantity: the length, or a square of the same area. */
export function toSizes(l: ConceptLine, u: PricedUnit): ConceptLine {
  if (isLength(u)) return { ...l, length_mm: +(l.quantity * u.length_mm).toFixed(3), count: 1, waste_pct: null };
  const side = +Math.sqrt(l.quantity * u.width_mm * u.height_mm).toFixed(3);
  return { ...l, width_mm: side, height_mm: side, count: 1, waste_pct: 0 };
}

/** Drop the sizes and keep the fraction they came to. */
export function toQuantity(l: ConceptLine, quantity: number): ConceptLine {
  const out: ConceptLine = { ...l, quantity };
  for (const k of SIZE_KEYS) delete out[k];
  return out;
}

// Standard Parts page: API types and pure helpers (tested with npm test).

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
}

export interface LibrarySubsection {
  number: string;
  title: string;
  notes: string[];
  parts: LibraryPart[];
}

export interface Library {
  sections: { number: string; title: string; subsections: LibrarySubsection[] }[];
  about: { title: string; lines: string[] }[];
  fx: Record<string, number>;
  quantities: number[];
  room_share: number;
  pricing: { vat_rate: number; dtc_factory_share: number };
}

export interface ConceptLine {
  part_id: string;
  quantity: number;
  note: string;
  option: number;
}

export type Verdict = "room" | "tight" | "over";

export interface CostLine extends ConceptLine {
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

/** Concept lines as sent to the API, dropping fields the server adds. */
export function plainLines(lines: ConceptLine[]): ConceptLine[] {
  return lines.map(({ part_id, quantity, note, option }) => ({ part_id, quantity, note, option }));
}

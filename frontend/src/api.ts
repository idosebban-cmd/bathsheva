// Typed client for the FastAPI backend. All calls go through the Vite proxy.

export type PowerType = "mains" | "battery" | "passive" | "undecided";

export interface Requirements {
  approx_dimensions: { height_mm: number | null; width_mm: number | null; depth_mm: number | null };
  target_retail_price: { amount: number | null; currency: string };
  production_volume: number | null;
  target_unit_cost: { amount: number | null; currency: string };
  intended_markets: string[];
  power_type: PowerType;
  battery_runtime_h?: number | null;
  preferred_materials: string[];
  preferred_finishes: string[];
  functional_requirements: string[];
  environmental_requirements: string[];
}

export interface ImageInfo {
  id: number;
  filename: string;
  path: string;
  kind: string;
  caption: string;
  uploaded_at: string;
}

export interface ProductTemplate {
  key: string;
  label: string;
  summary: string;
  noun: string;
}

export interface ProjectSummary {
  id: number;
  name: string;
  slug: string;
  description: string;
  template: string | null;
  created_at: string;
  updated_at: string;
}

export interface Project extends ProjectSummary {
  requirements: Requirements;
  assumed_fields: string[];
  images: ImageInfo[];
}

export interface Part {
  id: number;
  project_id: number;
  parent_id: number | null;
  cad_key: string | null;
  name: string;
  function: string;
  quantity: number;
  material_category: string;
  material: string;
  process: string;
  finish: string;
  traits: string[];
  dimensions: string;
  tolerances: string;
  supplier_notes: string;
  cost_low: number | null;
  cost_high: number | null;
  open_questions: string[];
  sort_order: number;
}

export type PartInput = Omit<Part, "id" | "project_id">;

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
  }
}
export { ApiError };

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(url: string) => request<T>("GET", url),
  post: <T>(url: string, body?: unknown) => request<T>("POST", url, body),
  patch: <T>(url: string, body?: unknown) => request<T>("PATCH", url, body),
  put: <T>(url: string, body?: unknown) => request<T>("PUT", url, body),
  del: (url: string) => request<void>("DELETE", url),
};

export const fileUrl = (path: string) => `/files/${path}`;

export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (Array.isArray(e.detail)) {
      return e.detail.map((d: { msg?: string; loc?: unknown[] }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`).join("; ");
    }
    if (typeof e.detail === "string") return e.detail;
    return JSON.stringify(e.detail);
  }
  return e instanceof Error ? e.message : String(e);
}

export interface ParamDef {
  key: string;
  label: string;
  group: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  integer: boolean;
  help: string;
}

export interface ValidationIssue {
  param: string | null;
  message: string;
  level: "error" | "warning";
}

export interface ValidationResult {
  ok: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface CadOutput {
  id: number;
  part_key: string | null;
  format: "step" | "stl" | "glb";
  path: string;
}

export interface CadModel {
  id: number;
  version: number;
  generator: string;
  parameters: Record<string, number>;
  part_info: Record<string, { size_mm: number[]; z_range_mm: number[]; volume_mm3: number; valid: boolean }>;
  created_at: string;
  outputs: CadOutput[];
}

export interface WallLimit {
  process_name: string;
  min: number;
  max: number;
  typical_min: number;
  typical_max: number;
  verified: boolean;
}

export interface CadState {
  mass?: { total_kg: number; target_kg: number | null; status: string; note: string; parts_kg: Record<string, number> } | null;
  generator: string;
  product: { key: string; label: string; noun: string; cad_note: string; mass_part: string };
  param_defs: ParamDef[];
  parameters: Record<string, number>;
  derived: Record<string, unknown>;
  production_changes?: { feature: string; prototype: string; production: string }[];
  validation: ValidationResult;
  wall_limits: Record<string, WallLimit>;
  latest: CadModel | null;
}

export interface RuntimeLoad {
  part: string | null;
  name: string;
  watts: number;
  hours_alone: number | null;
  source: string;
  verified: boolean;
}

export interface Runtime {
  applicable: boolean;
  reason?: string;
  hours?: number | null;
  target_h?: number | null;
  status?: "pass" | "close" | "fail" | "unknown";
  battery_wh?: number;
  delivered_wh?: number;
  load_w?: number;
  loads?: RuntimeLoad[];
  assumptions?: Record<string, string | number>;
  unverified?: boolean;
  note?: string;
  without_tower_light_h?: number | null;
  compliance?: string[];
}

export interface TemplateUpgradePlan {
  needed: boolean;
  remove: { cad_key: string; name: string; quotes: number }[];
  add: { cad_key: string; name: string }[];
  requirements: string[];
  decisions: string[];
  finishes?: { cad_key: string; name: string; from: string; to: string }[];
  done?: boolean;
}

export interface SourceRef {
  kind: string;
  key: string;
  source: string;
  confidence: "low" | "medium" | "high";
  verified: boolean;
}

export interface SafetyFlag {
  key: string;
  message: string;
  verify_with: string;
  verified: boolean;
}

export interface Alternative {
  process_key: string;
  process_name: string;
  material_key: string | null;
  material_name: string | null;
  when_to_prefer: string;
  why_not_chosen: string[];
  tooling_cost: string;
  score: number;
}

export interface Recommendation {
  part_id: number;
  part_key: string | null;
  part_name: string;
  status: "ok" | "no_match";
  recommendation: { process_key: string; process_name: string; material_key: string; material_name: string; finish: string } | null;
  summary: string;
  reason: string[];
  assumptions: string[];
  confidence: "low" | "medium" | "high";
  confidence_reason: string;
  alternatives: Alternative[];
  excluded: { process_key: string; process_name: string; reason: string; constraint?: string | null }[];
  constraints?: { key: string; name: string; message: string; scope: string; requirement: string; excluded_processes: string[]; violations: string[] }[];
  volume_sensitivity?: { volume: number; process_key: string; process_name: string }[];
  open_questions: string[];
  risks: string[];
  technical: Record<string, string | string[]>;
  safety_flags: SafetyFlag[];
  sources: SourceRef[];
  uses_unverified_data: boolean;
  inputs: Record<string, unknown>;
  decision: { id: number; status: string; chosen: Record<string, string>; note: string; updated_at: string } | null;
}

export interface OpenDecision {
  topic: string;
  question: string;
  options: string[];
  impact: string;
  current: string | null;
  open: boolean;
}

export interface RecommendationsResponse {
  recommendations: Recommendation[];
  open_decisions: OpenDecision[];
  llm: { enabled: boolean; provider: string };
}

export interface Explanation {
  plain_summary: string;
  tradeoffs: string[];
  questions_to_consider: string[];
  caveats: string[];
}

export interface BomRow {
  item: string;
  level: number;
  part_id: number | null;
  cad_key: string | null;
  name: string;
  quantity: number;
  material: string;
  process: string;
  finish: string;
  size_mm: string;
  status: "decided" | "recommended" | "TBD" | "derived";
  cost_low: number | null;
  cost_high: number | null;
  supplier_notes: string;
  flags: string[];
  derived: boolean;
}

export interface Bom {
  rows: BomRow[];
  total: { low: number; high: number; priced_items: number; total_items: number; complete: boolean };
  cad_version: number | null;
  notes: string[];
}

export interface DfmCheck {
  area: string;
  level: "pass" | "info" | "warning" | "fail";
  title: string;
  detail: string;
  unverified: boolean;
  part: string | null;
}

export interface DfmReport {
  project: string;
  generated_at: string;
  cad_version: number | null;
  summary: { fail: number; warning: number; info: number; pass: number; safety_items: number; open_questions: number; unverified_checks: number };
  checks: DfmCheck[];
  parts: {
    part_id: number;
    name: string;
    process: string;
    material: string;
    basis: string;
    decision: string | null;
    confidence: string | null;
    risks: string[];
    safety_flags: SafetyFlag[];
    open_questions: string[];
    uses_unverified_data: boolean;
  }[];
  safety: (SafetyFlag & { part: string })[];
  open_questions: { part: string; question: string }[];
  assumptions: string[];
  disclaimer: string;
}

export interface RevisionSummary {
  id: number;
  number: number;
  note: string;
  created_at: string;
}

export interface Snapshot {
  schema: number;
  project: { name: string; description: string; template: string | null };
  requirements: Requirements;
  assumed_fields: string[];
  cad_parameters: Record<string, number> | null;
  cad_model: CadModel | null;
  parts: Part[];
  decisions: { id: number; part_id: number | null; topic: string; status: string; chosen: Record<string, string>; note: string; created_at: string }[];
  recommendations: Recommendation[];
  images: ImageInfo[];
}

export interface Revision extends RevisionSummary {
  snapshot: Snapshot;
}

export interface QuoteComparison {
  status: "no_estimate" | "currency_mismatch" | "below" | "within" | "above";
  diff: number | null;
  diff_pct: number | null;
  text: string;
}

export interface ExternalQuote {
  id: number;
  part_id: number;
  revision_id: number | null;
  revision_number: number | null;
  source: string;
  quote_date: string;
  process: string;
  material: string;
  finish: string;
  quantity: number;
  unit_price: number;
  currency: string;
  total_price: number;
  lead_time_days: number | null;
  dfm_notes: string;
  attachment_path: string | null;
  attachment_filename: string | null;
  created_at: string;
  comparison: QuoteComparison;
}

export interface PartQuotes {
  part_id: number;
  estimate: { low: number; high: number; currency: string; basis: string } | null;
  quotes: ExternalQuote[];
  note: string;
}

export interface CostLine {
  category: string;
  part_id: number | null;
  item_id: number | null;
  label: string;
  low: number;
  mid: number;
  high: number;
  keys: string[];
  explanation: string;
  unverified: boolean;
  confidence: string;
}

export interface CostRange {
  quantity: number;
  low: number;
  mid: number;
  high: number;
  worst_low: number;
  worst_high: number;
  raw_mid?: number;
  is_project_volume?: boolean;
}

export interface SensitivityRow {
  key: string;
  label: string;
  group: string;
  unit: string;
  value: number;
  confidence: string;
  verified: boolean;
  source: string;
  cost_down: number;
  cost_up: number;
  swing: number;
  swing_pct: number;
}

export interface CostAssumption {
  key: string;
  label: string;
  group: string;
  unit: string;
  low: number;
  high: number;
  widened: [number, number];
  confidence: string;
  verified: boolean;
  source: string;
}

export interface CostReport {
  currency: string;
  reference_quantity: number;
  reference_basis: string;
  unit_cost: CostRange;
  volumes: CostRange[];
  parts: {
    part_id: number;
    name: string;
    quantity: number;
    process: string;
    material: string;
    finish: string | null;
    basis: string;
    lines: CostLine[];
    low: number;
    mid: number;
    high: number;
  }[];
  product_lines: CostLine[];
  categories: Record<string, { low: number; mid: number; high: number }>;
  sensitivity: { step: number; top: SensitivityRow[]; count: number };
  skipped: { name: string; reason: string }[];
  assumptions: CostAssumption[];
  spread: Record<string, number>;
  uses_unverified_data: boolean;
  has_items: boolean;
  can_load_defaults: boolean;
  notes: string[];
}

export interface CostItem {
  id: number;
  kind: "bought_in" | "assembly" | "packaging" | "finishing" | "one_off" | "other";
  name: string;
  quantity: number;
  unit: "pcs" | "min";
  unit_cost_low: number | null;
  unit_cost_high: number | null;
  price_key: string | null;
  source: string;
  confidence: "low" | "medium" | "high";
  verified: boolean;
  notes: string;
  sort_order: number;
  price_basis: "trade_volume" | "distributor_small_qty" | "retail" | "model_estimate";
  basis_quantity: number | null;
  discount_class: string | null;
}

export interface VolumeDiscount {
  low: number;
  high: number;
  from_quantity: number;
  default: { low: number; high: number };
  edited: boolean;
  source: string;
  confidence: string;
  verified: boolean;
  plain_language: string;
}

export interface CostSettings {
  volume_discounts: Record<string, VolumeDiscount>;
}

// --- Factory Pack (RFQ) ---------------------------------------------------

export interface FactoryPackPart {
  cad_key: string;
  part_no: string;
  name: string;
  quantity: number;
  material: string;
  process: string;
  finish: string;
  size_mm: string;
  status: string;
  unverified: string[];
  safety: string[];
  drawing: string;
  step: string;
}

export interface FactoryPackCheck {
  check: string;
  ok: boolean;
  detail: string;
  level?: "warn";
}

export interface OpenQuestion {
  id: string;
  topic: string;
  question: string;
  why: string;
  proposed: string;
  answer: string;
  status: "open" | "resolved";
}

export interface FactoryPackSummary {
  cad_version: number | null;
  ready: boolean;
  parts: FactoryPackPart[];
  bought_in: { name: string; quantity: number; electronics: boolean; group: "electronics" | "operation" | "hardware" }[];
  hardware: { item: string; name: string; quantity: number; material: string; notes: string }[];
  brass_parts: { part_no: string; name: string; near_net: string }[];
  consistency: FactoryPackCheck[];
  open_questions: OpenQuestion[];
  placeholders: string[];
  contact: Record<string, string>;
  contact_fields: { key: string; label: string; placeholder: string }[];
  missing_contact: string[];
  electronics_rfq_markdown: string;
  quantity_tiers: number[];
  mass: { total_kg: number; target_kg: number | null; status: string; note: string; parts_kg: Record<string, number> } | null;
  unverified: string[];
  safety: string[];
  compliance: string[];
  rfq_markdown: string;
  notes: string[];
}

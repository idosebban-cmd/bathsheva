// Typed client for the FastAPI backend. All calls go through the Vite proxy.

export type PowerType = "mains" | "battery" | "passive" | "undecided";

export interface Requirements {
  approx_dimensions: { height_mm: number | null; width_mm: number | null; depth_mm: number | null };
  target_retail_price: { amount: number | null; currency: string };
  production_volume: number | null;
  target_unit_cost: { amount: number | null; currency: string };
  intended_markets: string[];
  power_type: PowerType;
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
  generator: string;
  param_defs: ParamDef[];
  parameters: Record<string, number>;
  derived: Record<string, number>;
  validation: ValidationResult;
  wall_limits: Record<string, WallLimit>;
  latest: CadModel | null;
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
  excluded: { process_key: string; process_name: string; reason: string }[];
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

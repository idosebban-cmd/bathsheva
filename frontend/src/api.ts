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

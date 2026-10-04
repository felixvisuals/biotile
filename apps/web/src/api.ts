// Thin typed client for the BIOTILE API. The Tripo key never reaches the browser.

export type Check = { id: string; status: "pass" | "warn" | "fail"; value: number | null; limit: number | null; message: string };

export type FunctionalParams = {
  template: "moss_nests" | "diagonal_cascade" | "none";
  nest_spacing_mm: number;
  nest_size_mm: number;
  nest_depth_mm: number;
  rills: boolean;
  channel_depth_mm: number;
  channel_width_mm: number;
  channel_count: number;
  anchor_holes: boolean;
  direction: "down_right" | "down_left";
  seed: number;
};

export type TileParams = {
  macro_depth_mm: number;
  meso_depth_mm: number;
  macro_meso_cutoff_mm: number;
  orientation_mode: "auto_along_flow" | "cross" | "none";
  functional: FunctionalParams;
  edge_mode: "periodic" | "framed";
  texture_period_mm: number;
  shape: "square" | "hex";
  tile_size_mm: number;
  front_code: boolean;
  material: "clay" | "concrete" | "lime" | "loam";
  process: "press_mould" | "matrix_down" | "stamp_down";
  tool_material: string;
  shrink_pct: number;
  printer: string;
  resolution_px: number;
};

export type DesignSummary = {
  id: string;
  code: string | null;
  title: string;
  title_en: string | null;
  description: string | null;
  description_en: string | null;
  simulated: boolean;
  source_type: "photo" | "text" | "procedural" | "hybrid";
  surface_type: string | null;
  status: "draft" | "published" | "hidden";
  stage: "new" | "generating" | "ready" | "exported" | "failed";
  parent_design_id: string | null;
  is_original: boolean;
  license: string;
  preview_url: string | null;
  preview_3x3_url: string | null;
  tripo_render_url: string | null;
  instance_count: number;
  created_at: string;
  pipeline_version: string | null;
  is_mine?: boolean;
  shape?: "square" | "hex";
};

export type Design = DesignSummary & {
  params: TileParams;
  metrics: Record<string, any>;
  checks: Check[];
  model_seed: number | null;
  texture_seed: number | null;
  raster_seed: number;
  tripo_model_version: string | null;
  tripo_texture_version: string | null;
  heightfield_sha256: string | null;
  has_package: boolean;
  interface_version: string | null;
  lineage: { id: string; code: string | null; title: string; title_en: string | null }[];
  children: { id: string; code: string | null; title: string; title_en: string | null }[];
};

export type Preview = {
  design_id: string;
  code: string | null;
  shape: "square" | "hex";
  size_mm: number;
  bbox_mm: [number, number];
  thickness_mm: number;
  front: { nx: number; ny: number; b64: string };
  wall: { n: number; extent_mm: number; b64: string };
  joints: [number, number][][];
  mould_mm: [number, number];
  checks: Check[];
  bed: Record<string, { extent_mm: number }>;
  structure_angle_deg: number;
  anisotropy: number;
  rotation_deg: number;
  params: TileParams;
  tool_scale: number;
};

export type Job = { id: string; design_id: string; kind: string; status: "queued" | "running" | "success" | "failed"; progress: number; step: string | null; error: string | null; error_key: string | null; simulated?: boolean };

export type LibraryEntry = {
  id: string;
  kind: "sample" | "ref_flat" | "ref_geo";
  name: { en: string; de: string };
  rationale: { en: string; de: string };
  recommended_functional_template: string;
  mock_fixture?: string;
};

export type Species = { name: string; taxon_ref?: string | null; group: string | null; certainty: string };
export type Observation = { id: string; observed_at: string; photo_url: string | null; species: Species[]; notes: string | null; weight_g: number | null; observer_role: string; green_fraction: number | null };
export type Geo = { lat: number; lon: number; precision: "exact" | "approx"; visibility?: string };
export type Instance = {
  id: string; is_mine: boolean; geo: Geo | null; mounting_detail: string | null; design_shape: string; design_preview_url: string | null; design_id: string; design_code: string; design_title: string; design_title_en: string | null; material: string; process: string; format: string; stage: number;
  orientation_deg: number; inclination_deg: number | null; booster: boolean; booster_recipe: string | null; mounting_adapter: string | null;
  installed_date: string | null; cast_date: string | null; shading: string | null; location_coarse: string | null; status: string; channels: string;
  height_above_ground_m: number | null; notes: string | null; observations: Observation[];
};

export type Quota = { mode: "mock" | "live"; limit: number; used: number; remaining: number; fallback?: boolean; mock?: Quota };
export type Me = { id: string; name: string; email: string; type: string; quota: Quota };

export type Lookup =
  | { kind: "instance"; instance: Instance }
  | { kind: "design"; design: DesignSummary; instances: Instance[] };

export type Config = {
  tile_sizes_mm: number[];
  invite_required: boolean;
  jury_login: boolean;
  tripo_mode: "mock" | "live";
  tripo_key_configured: boolean;
  pipeline_version: string;
  printers: Record<string, { label: string; volume_mm: number[] }>;
  limits: Record<string, any>;
};

export class ApiError extends Error {
  constructor(public status: number, public key: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let key = "errors.generic";
    let message = res.statusText;
    try {
      const body = await res.json();
      key = body?.detail?.key ?? key;
      message = body?.detail?.message ?? JSON.stringify(body?.detail ?? body);
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, key, message);
  }
  return res.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  me: () => request<Me | null>("/api/auth/me"),
  login: (email: string, password: string) => request<Me>("/api/auth/login", json("POST", { email, password })),
  register: (body: { name: string; email: string; password: string; type: string; invite_code?: string }) =>
    request<Me>("/api/auth/register", json("POST", body)),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  config: () => request<Config>("/api/config"),
  library: () => request<LibraryEntry[]>("/api/library"),
  designs: (status = "published") => request<DesignSummary[]>(`/api/designs?status=${status}`),
  design: (id: string) => request<Design & { is_mine?: boolean }>(`/api/designs/${id}`),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ upload_id: string; width: number; height: number; warnings: string[] }>("/api/uploads", { method: "POST", body: fd });
  },
  createDesign: (body: { title: string; source_type: "photo" | "procedural"; upload_id?: string; surface_type?: string; description?: string; enable_image_autofix?: boolean }) =>
    request<Design>("/api/designs", json("POST", body)),
  generate: (id: string) => request<{ job_id: string }>(`/api/designs/${id}/generate`, { method: "POST" }),
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  latestJob: (designId: string, kind: "generate" | "export") => request<Job>(`/api/designs/${designId}/job?kind=${kind}`),
  preview: (id: string, n?: number) => request<Preview>(`/api/designs/${id}/preview${n ? `?n=${n}` : ""}`),
  patchParams: (id: string, updates: Record<string, unknown>) => request<Preview>(`/api/designs/${id}/params`, json("PATCH", updates)),
  exportDesign: (id: string) => request<{ job_id: string }>(`/api/designs/${id}/export`, { method: "POST" }),
  packageUrl: (id: string) => `/api/designs/${id}/package`,
  publish: (id: string) => request<Design>(`/api/designs/${id}/publish`, json("POST", { license_confirmed: true })),
  remix: (id: string) => request<Design>(`/api/designs/${id}/remix`, { method: "POST" }),
  designInstances: (id: string) => request<Instance[]>(`/api/designs/${id}/instances`),
  createInstance: (body: Record<string, unknown>) => request<Instance>("/api/instances", json("POST", body)),
  locations: () => request<{ id: string; lat: number; lon: number; title: string; title_en: string | null; place: string | null; preview_url: string | null }[]>("/api/locations"),
  jury: () => request<Me>("/api/auth/jury", { method: "POST" }),
  lookup: (code: string) => request<Lookup>(`/api/lookup/${encodeURIComponent(code.trim())}`),
  instance: (id: string) => request<Instance>(`/api/instances/${encodeURIComponent(id)}`),
  referenceCardUrl: (id: string) => `/api/instances/${encodeURIComponent(id)}/reference-card.pdf`,
  addObservation: (id: string, fd: FormData) => request<Instance>(`/api/instances/${encodeURIComponent(id)}/observations`, { method: "POST", body: fd }),
};

export function decodeHeights(b64: string): Float32Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Float32Array(bytes.buffer);
}

export async function pollJob(id: string, onUpdate: (j: Job) => void, intervalMs = 700): Promise<Job> {
  for (;;) {
    const j = await api.job(id);
    onUpdate(j);
    if (j.status === "success" || j.status === "failed") return j;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

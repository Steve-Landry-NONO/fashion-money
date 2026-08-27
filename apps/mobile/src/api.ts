export type Wallet = {
  period: string;
  base: number;
  rollover_in: number;
  spent: number;
  available: number;
};

export type Capture = {
  capture_id: string;
  look_id: string;
  status: string;
};

export type LookPiece = {
  id: string;
  category_raw: string | null;
  category: string;
  color: string | null;
  cut: string | null;
  material: string | null;
  swatch: string | null;
  confidence: number | null;
  owned_pct: number;
  is_owned: boolean;
  match_reason: string | null;
};

export type Outfit = {
  id: string;
  position: number;
  style: string | null;
  is_representative: boolean;
  pieces: LookPiece[];
};

export type Look = {
  id: string;
  style: string | null;
  image_type: "single_outfit" | "collage";
  dominant_palette: string[];
  representative_outfit_index: number;
  outfits: Outfit[];
  pieces: LookPiece[];
  score_look: number;
};

export type Option = {
  id: string;
  price: number;
  merchant: string | null;
  affiliate_url: string | null;
  similarity: number | null;
  purchase_score: number | null;
  is_best: boolean;
};

export type Evaluation = {
  verdict: "fits" | "tight" | "over";
  available: number;
  available_after: number;
  price: number;
  issues: Array<Record<string, unknown>>;
};

const authHeader = {Authorization: "Bearer dev-token"};
const jsonHeaders = {...authHeader, "Content-Type": "application/json"};

async function request<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
    ...init,
    headers: {...jsonHeaders, ...(init?.headers ?? {})},
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${body || response.statusText}`);
  }
  return (await response.json()) as T;
}

function imageMeta(uri: string): {name: string; type: string} {
  const clean = (uri.split("?")[0] ?? uri).toLowerCase();
  if (clean.endsWith(".png")) return {name: "look.png", type: "image/png"};
  if (clean.endsWith(".webp")) return {name: "look.webp", type: "image/webp"};
  return {name: "look.jpg", type: "image/jpeg"};
}

async function uploadCapture(baseUrl: string, imageUri: string): Promise<Capture> {
  const meta = imageMeta(imageUri);
  const form = new FormData();
  form.append("file", {uri: imageUri, name: meta.name, type: meta.type} as unknown as Blob);
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/captures/upload`, {
    method: "POST",
    headers: authHeader,
    body: form,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${body || response.statusText}`);
  }
  return (await response.json()) as Capture;
}

export const api = {
  setBudget: (baseUrl: string, baseAmount: number) =>
    request<Wallet>(baseUrl, "/budget", {
      method: "POST",
      body: JSON.stringify({base_amount: baseAmount}),
    }),
  wallet: (baseUrl: string) => request<Wallet>(baseUrl, "/wallet"),
  createCapture: uploadCapture,
  look: (baseUrl: string, lookId: string) => request<Look>(baseUrl, `/looks/${lookId}`),
  selectOutfit: (baseUrl: string, lookId: string, outfitId: string) =>
    request<{look_id: string; outfit_id: string; representative_outfit_index: number}>(
      baseUrl,
      `/looks/${lookId}/selection`,
      {method: "POST", body: JSON.stringify({outfit_id: outfitId})},
    ),
  gaps: (baseUrl: string, lookId: string, outfitId?: string) =>
    request<{missing: string[]}>(
      baseUrl,
      `/looks/${lookId}/gaps${outfitId ? `?outfit_id=${encodeURIComponent(outfitId)}` : ""}`,
    ),
  options: (baseUrl: string, pieceId: string) =>
    request<{options: Option[]}>(baseUrl, `/gaps/${pieceId}/options`),
  evaluate: (baseUrl: string, optionId: string) =>
    request<Evaluation>(baseUrl, "/decisions/evaluate", {
      method: "POST",
      body: JSON.stringify({option_id: optionId}),
    }),
  takeAction: (baseUrl: string, optionId: string, action: string) =>
    request<{decision_id: string; action: string}>(baseUrl, "/decisions/actions", {
      method: "POST",
      body: JSON.stringify({option_id: optionId, action}),
    }),
  confirmPurchase: (baseUrl: string, optionId: string, idempotencyKey: string) =>
    request<{purchase_id: string; wardrobe_item_id: string; wallet: Wallet}>(baseUrl, "/purchases/confirm", {
      method: "POST",
      body: JSON.stringify({option_id: optionId, idempotency_key: idempotencyKey}),
    }),
};

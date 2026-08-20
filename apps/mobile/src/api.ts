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
  category: string;
  color: string | null;
  cut: string | null;
  material: string | null;
  swatch: string | null;
  owned_pct: number;
  is_owned: boolean;
  match_reason: string | null;
};

export type Look = {
  id: string;
  style: string | null;
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

const headers = {
  Authorization: "Bearer dev-token",
  "Content-Type": "application/json",
};

async function request<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
    ...init,
    headers: {...headers, ...(init?.headers ?? {})},
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${body || response.statusText}`);
  }
  return (await response.json()) as T;
}

export const api = {
  setBudget: (baseUrl: string, baseAmount: number) =>
    request<Wallet>(baseUrl, "/budget", {
      method: "POST",
      body: JSON.stringify({base_amount: baseAmount}),
    }),
  wallet: (baseUrl: string) => request<Wallet>(baseUrl, "/wallet"),
  createCapture: (baseUrl: string, imageRef?: string | null) =>
    request<Capture>(baseUrl, "/captures", {
      method: "POST",
      body: JSON.stringify({image_ref: imageRef ?? null}),
    }),
  look: (baseUrl: string, lookId: string) => request<Look>(baseUrl, `/looks/${lookId}`),
  gaps: (baseUrl: string, lookId: string) => request<{missing: string[]}>(baseUrl, `/looks/${lookId}/gaps`),
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

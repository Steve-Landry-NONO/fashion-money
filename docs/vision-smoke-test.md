# Vision smoke test protocol

Goal: validate the real `image -> outfits -> normalized pieces` boundary before replacing Product Search.

## Dataset

Use 3 to 5 deliberately different fashion inspiration screenshots. The current reference set contains four multi-look collages. Do not commit screenshots; keep them in `backend/smoke_inputs/`.

## Run with Groq

Create `backend/.env` locally and set:

```env
DECOMPOSITION_PROVIDER=groq
GROQ_API_KEY=your_local_key
VISION_MODEL=qwen/qwen3.8-27b
```

From `backend/` on PowerShell:

```powershell
python scripts/vision_smoke_test.py smoke_inputs --provider groq --output artifacts/vision-smoke-report.json
```

Qwen 3.8 is the current Groq baseline. On the four reference collages it reached 4/4 successful structured responses, whereas Qwen 3.6 remained unstable on JSON validation.

## V2 output contract

Vision returns:

- `image_type`: `single_outfit` or `collage`;
- overall `style`;
- `dominant_palette[]`;
- `outfits[]`, one entry per distinct visible outfit/person;
- each outfit has `style` and `pieces[]`;
- each piece keeps `category_raw` plus a deterministic normalized `category`;
- optional `color`, `cut`, `material`, `swatch`, and `confidence`;
- `representative_outfit_index`.

The full contract is now persisted. `Look` stores image type, palette and representative index; `LookOutfit` stores every detected outfit; `LookPiece` stores outfit membership, raw category and confidence. The current mobile client remains backward-compatible because `GET /looks/{id}` still exposes top-level `pieces[]` for the representative outfit while also returning `outfits[]` for the upcoming selection UI.

## Category normalization

The provider layer normalizes obvious aliases before Matching/Product Search, for example:

- `pants`, `slacks` -> `trousers`;
- `polo shirt` -> `polo`;
- `tee`, `t shirt` -> `t-shirt`;
- loafer variants -> `shoes`.

The raw category is retained so normalization remains auditable.

## What to review

For every image, check:

1. **Collage segmentation** — garments from different people must never be merged into one outfit.
2. **Pieces per outfit** — target roughly 3–5 material wardrobe pieces per visible look rather than 10+ merged pieces.
3. **Category stability** — normalized categories should reduce synonym fragmentation.
4. **Color quality** — semantic color should be useful for ranking.
5. **Cut/material uncertainty** — null is preferable to unsupported specificity.
6. **Confidence calibration** — low-confidence attributes should not dominate matching.
7. **Matching consequence** — category has highest weight, then color, then cut; material must remain weak evidence in V1.

## Automatic report signals

The report contains success ratio, collages detected, average outfit count, average/min/max pieces per outfit, raw vs normalized category counts, missing attribute ratios, confidence coverage, and all structured outputs.

## Current gate result

Qwen 3.8 passes the transport/structured-output gate on the four reference collages: 4 attempted, 4 succeeded, 0 failed. It also preserves uncertainty better on material than the earlier Qwen 3.6 runs. Segmentation is usable but not perfect: two reference collages produced an extra one-piece outfit, so low-information/ambiguous outfit handling remains a known issue rather than a blocker for the provider boundary itself.

A provider-side guardrail now prevents a one-piece ghost outfit from being auto-selected as representative whenever a richer outfit exists. This is only a safety fallback: the product answer for multi-outfit captures remains explicit user selection — **« Quel look veux-tu recréer ? »**.

Groq retries use three distinct prompts rather than replaying an identical deterministic request.

## Tests

CI covers the deterministic contract logic without making live provider calls:

- category alias normalization;
- empty-outfit filtering;
- promotion to collage when multiple valid outfits survive;
- representative-index clamp / ghost-outfit guardrail;
- persistence of all outfits;
- persistence of `category_raw` and `confidence`.

Live Groq benchmarking remains local-only.

## Gate before real Product Search

Proceed when the same four screenshots show:

- reliable structured responses (4/4 on the reference set);
- separation of distinct outfits good enough that the user can select the intended outfit;
- representative outfits with coherent compositions in most cases;
- normalized categories suitable for stable search queries;
- no systematic overconfidence on fabric/cut;
- material treated as weak evidence rather than a hard matching constraint;
- full V2 contract surviving persistence so outfit selection can be built without re-running Vision.

Do not silently auto-select ambiguous one-piece outfits in the product flow. Multi-outfit selection or ambiguity handling must protect Product Search from obvious segmentation noise.

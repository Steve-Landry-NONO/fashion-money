# Vision smoke test protocol

Goal: validate the real `image -> outfits -> normalized pieces` boundary before replacing Product Search.

## Dataset

Use 3 to 5 deliberately different fashion inspiration screenshots. The current reference set contains four multi-look collages. Do not commit screenshots; keep them in `backend/smoke_inputs/`.

## Run with Groq

Create `backend/.env` locally and set:

```env
DECOMPOSITION_PROVIDER=groq
GROQ_API_KEY=your_local_key
VISION_MODEL=qwen/qwen3.6-27b
```

From `backend/` on PowerShell:

```powershell
python scripts/vision_smoke_test.py smoke_inputs --provider groq --output artifacts/vision-smoke-report.json
```

## V2 output contract

Vision must return:

- `image_type`: `single_outfit` or `collage`
- overall `style`
- `dominant_palette[]`
- `outfits[]`, one entry per distinct visible outfit/person
- each outfit has `style` and `pieces[]`
- each piece keeps `category_raw` plus a deterministic normalized `category`
- optional `color`, `cut`, `material`, `swatch`, and `confidence`
- `representative_outfit_index`

The application remains backward-compatible for the current vertical slice: downstream matching consumes only the representative outfit through `DecomposedLook.pieces`. Multi-outfit selection is a later UI concern.

## Category normalization

The provider layer normalizes obvious aliases before Matching/Product Search, for example:

- `pants`, `slacks` -> `trousers`
- `polo shirt` -> `polo`
- `tee`, `t shirt` -> `t-shirt`
- loafer variants -> `shoes`

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

## Gate before real Product Search

Proceed only if the same four screenshots show:

- reliable separation of distinct outfits;
- representative outfits with coherent 3–5-piece compositions in most cases;
- materially lower normalized category fragmentation than raw category fragmentation;
- no systematic overconfidence on fabric/cut;
- attributes stable enough to construct product-search queries without poisoning wardrobe matching.

If these conditions fail, iterate on prompt/schema/taxonomy before merchant integration.

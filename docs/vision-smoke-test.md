# Vision smoke test protocol

Goal: validate the real `image -> style + pieces` boundary before replacing Product Search.

## Dataset

Use 3 to 5 deliberately different fashion inspiration screenshots. Prefer diversity in:

- casual vs formal
- light vs dark palette
- layered vs simple outfits
- trousers vs skirt/dress/shorts when relevant
- sneakers vs leather shoes/boots
- clear vs partially occluded garments

Do not commit the screenshots. Put them locally in `backend/smoke_inputs/`.

## Run

From `backend/`:

```bash
export OPENAI_API_KEY="..."
export VISION_MODEL="gpt-5.6-luna"
python scripts/vision_smoke_test.py smoke_inputs \
  --output artifacts/vision-smoke-report.json
```

The harness intentionally reads local files through the same `OpenAIDecompositionProvider` used by the application, while bypassing MinIO so the test isolates Vision quality rather than storage availability.

## What to review manually

For every image, compare the source screenshot with the returned structure and score:

1. **Category stability** — are garments named consistently across images? Avoid synonyms that will fragment matching (`trousers` vs `pants`, `overshirt` vs `shirt jacket`) unless the distinction is useful.
2. **Piece coverage** — are all visually important wearable pieces present? Are accessories/noise incorrectly included?
3. **Color quality** — is the semantic color useful for matching? Is the swatch directionally correct?
4. **Cut quality** — is the cut visible enough to justify the label? Track hallucinated specificity.
5. **Material quality** — materials should be omitted when the image does not support them rather than confidently guessed.
6. **Style quality** — short, reusable style description rather than brand or influencer commentary.
7. **Matching consequence** — would the extracted attributes lead the current attribute matcher toward the right wardrobe item, or create false positives/false negatives?

## Quantitative signals produced automatically

The JSON report contains:

- image count
- min / max / average number of detected pieces
- unique normalized categories
- missing-value ratios for color, cut, material and swatch
- raw structured result per screenshot

Missing values are not automatically bad. In particular, a high material-missing rate can be preferable to hallucinating material from a low-quality screenshot.

## Decision gate before Product Search

Proceed to real Product Search only if the smoke set suggests:

- core garment categories are stable enough to construct search queries;
- important pieces are rarely omitted;
- color is usable for ranking;
- cut/material errors do not systematically poison matching;
- output variability is understandable enough to normalize with a small taxonomy layer.

If not, improve the decomposition prompt/schema and add category normalization before integrating merchant catalogs.

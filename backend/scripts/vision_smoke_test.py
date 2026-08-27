# ruff: noqa: I001
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Any

from app.capture.providers import GroqDecompositionProvider, OpenAIDecompositionProvider
from app.capture.storage import StoredImage
from app.config import settings

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class FileSystemImageStorage:
    def get(self, image_ref: str) -> StoredImage:
        path = Path(image_ref)
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return StoredImage(key=image_ref, content_type=content_type, data=data)


def discover_images(root: Path) -> list[Path]:
    return sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES)


def missing_ratio(values: list[str | None]) -> float:
    if not values:
        return 0.0
    return sum(value is None or not str(value).strip() for value in values) / len(values)


def summarize(results: list[dict[str, Any]], errors: list[dict[str, str]]) -> dict[str, Any]:
    outfits = [outfit for result in results for outfit in result["outfits"]]
    all_pieces = [piece for outfit in outfits for piece in outfit["pieces"]]
    outfit_counts = [result["outfit_count"] for result in results]
    piece_counts = [len(outfit["pieces"]) for outfit in outfits]
    normalized = [piece["category"] for piece in all_pieces]
    raw = [piece["category_raw"] for piece in all_pieces]
    attempted = len(results) + len(errors)
    return {
        "images_attempted": attempted,
        "images_succeeded": len(results),
        "images_failed": len(errors),
        "success_ratio": round(len(results) / attempted, 3) if attempted else 0,
        "collages_detected": sum(result["image_type"] == "collage" for result in results),
        "avg_outfit_count": round(mean(outfit_counts), 2) if outfit_counts else 0,
        "avg_pieces_per_outfit": round(mean(piece_counts), 2) if piece_counts else 0,
        "min_pieces_per_outfit": min(piece_counts, default=0),
        "max_pieces_per_outfit": max(piece_counts, default=0),
        "unique_raw_categories": sorted(set(raw)),
        "raw_category_count": len(set(raw)),
        "unique_normalized_categories": sorted(set(normalized)),
        "normalized_category_count": len(set(normalized)),
        "missing_color_ratio": round(missing_ratio([piece["color"] for piece in all_pieces]), 3),
        "missing_cut_ratio": round(missing_ratio([piece["cut"] for piece in all_pieces]), 3),
        "missing_material_ratio": round(missing_ratio([piece["material"] for piece in all_pieces]), 3),
        "missing_swatch_ratio": round(missing_ratio([piece["swatch"] for piece in all_pieces]), 3),
        "missing_confidence_ratio": round(missing_ratio([piece["confidence"] for piece in all_pieces]), 3),
    }


def build_provider(provider_name: str, storage: FileSystemImageStorage):
    if provider_name == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is required for the Groq smoke test")
        return GroqDecompositionProvider(storage=storage)
    if provider_name == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI smoke test")
        return OpenAIDecompositionProvider(storage=storage)
    raise ValueError("provider must be 'groq' or 'openai'")


def run(images_dir: Path, output: Path, provider_name: str) -> int:
    images = discover_images(images_dir)
    if not 3 <= len(images) <= 5:
        print(f"Expected 3 to 5 images in {images_dir}; found {len(images)}.", file=sys.stderr)
        return 2
    try:
        provider = build_provider(provider_name, FileSystemImageStorage())
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for image in images:
        try:
            look = provider.decompose(str(image))
        except Exception as exc:
            error = {"image": image.name, "error_type": type(exc).__name__, "message": str(exc)}
            errors.append(error)
            print(f"{image.name}: ERROR {error['error_type']} - {error['message']}", file=sys.stderr)
            continue

        result = {
            "image": image.name,
            "image_type": look.image_type,
            "style": look.style,
            "dominant_palette": look.dominant_palette,
            "outfit_count": len(look.outfits),
            "representative_outfit_index": look.representative_outfit_index,
            "outfits": [asdict(outfit) for outfit in look.outfits],
        }
        results.append(result)
        print(f"{image.name}: {look.image_type} | {look.style} -> {len(look.outfits)} outfits")
        for idx, outfit in enumerate(look.outfits):
            marker = "*" if idx == look.representative_outfit_index else " "
            print(f" {marker} outfit {idx}: {outfit.style} -> {len(outfit.pieces)} pieces")
            for piece in outfit.pieces:
                print(
                    f"    - {piece.category_raw} -> {piece.category} | color={piece.color} | "
                    f"cut={piece.cut} | material={piece.material} | confidence={piece.confidence}"
                )

    report = {
        "provider": provider_name,
        "vision_model": settings.vision_model,
        "results": results,
        "errors": errors,
        "summary": summarize(results, errors),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport written to {output}")
    return 0 if results else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the live Fashion Money vision smoke test.")
    parser.add_argument("images_dir", type=Path)
    parser.add_argument(
        "--provider",
        choices=("groq", "openai"),
        default=settings.decomposition_provider if settings.decomposition_provider in {"groq", "openai"} else "groq",
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/vision-smoke-report.json"))
    args = parser.parse_args()
    return run(args.images_dir, args.output, args.provider)


if __name__ == "__main__":
    raise SystemExit(main())

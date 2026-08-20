# ruff: noqa: I001
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Any

from app.capture.providers import OpenAIDecompositionProvider
from app.capture.storage import StoredImage


SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class FileSystemImageStorage:
    """Smoke-test adapter that reads local images without touching MinIO."""

    def get(self, image_ref: str) -> StoredImage:
        path = Path(image_ref)
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return StoredImage(key=image_ref, content_type=content_type, data=data)


def discover_images(root: Path) -> list[Path]:
    return sorted(
        path for path in root.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def missing_ratio(values: list[str | None]) -> float:
    if not values:
        return 0.0
    return sum(value is None or not str(value).strip() for value in values) / len(values)


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    piece_counts = [result["piece_count"] for result in results]
    all_pieces = [piece for result in results for piece in result["pieces"]]
    categories = [piece["category"] for piece in all_pieces]
    return {
        "images": len(results),
        "avg_piece_count": round(mean(piece_counts), 2) if piece_counts else 0,
        "min_piece_count": min(piece_counts, default=0),
        "max_piece_count": max(piece_counts, default=0),
        "unique_categories": sorted(set(categories)),
        "category_count": len(set(categories)),
        "missing_color_ratio": round(missing_ratio([piece["color"] for piece in all_pieces]), 3),
        "missing_cut_ratio": round(missing_ratio([piece["cut"] for piece in all_pieces]), 3),
        "missing_material_ratio": round(missing_ratio([piece["material"] for piece in all_pieces]), 3),
        "missing_swatch_ratio": round(missing_ratio([piece["swatch"] for piece in all_pieces]), 3),
    }


def run(images_dir: Path, output: Path) -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required for the live smoke test.", file=sys.stderr)
        return 2

    images = discover_images(images_dir)
    if not 3 <= len(images) <= 5:
        print(
            f"Expected 3 to 5 images in {images_dir}; found {len(images)}.",
            file=sys.stderr,
        )
        return 2

    provider = OpenAIDecompositionProvider(storage=FileSystemImageStorage())
    results: list[dict[str, Any]] = []

    for image in images:
        look = provider.decompose(str(image))
        result = {
            "image": image.name,
            "style": look.style,
            "piece_count": len(look.pieces),
            "pieces": [asdict(piece) for piece in look.pieces],
        }
        results.append(result)
        print(f"{image.name}: {look.style} -> {len(look.pieces)} pieces")
        for piece in look.pieces:
            print(
                "  - "
                f"{piece.category} | color={piece.color} | cut={piece.cut} | "
                f"material={piece.material} | swatch={piece.swatch}"
            )

    report = {
        "vision_model": os.getenv("VISION_MODEL", "gpt-5.6-luna"),
        "results": results,
        "summary": summarize(results),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport written to {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the live Fashion Money vision smoke test.")
    parser.add_argument("images_dir", type=Path, help="Directory containing 3 to 5 diverse look screenshots")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/vision-smoke-report.json"),
        help="JSON report path",
    )
    args = parser.parse_args()
    return run(args.images_dir, args.output)


if __name__ == "__main__":
    raise SystemExit(main())

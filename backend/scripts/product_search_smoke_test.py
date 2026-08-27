"""Live Product Search smoke benchmark.

Usage from backend/:
    PRODUCT_SEARCH_PROVIDER=shopify \
    SHOPIFY_UCP_PROFILE_URL=https://... \
    python scripts/product_search_smoke_test.py --output artifacts/product-search-smoke.json

The corpus mirrors representative normalized pieces produced by the Qwen 3.8
vision benchmark. Live calls are intentionally excluded from CI. For Shopify,
the harness performs tools/list before any coverage measurement so the real MCP
schema is captured before we trust the experimental request shape.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.capture.models import LookPiece
from app.catalog.providers import (
    SearchContext,
    ShopifyGlobalCatalogProvider,
    get_product_search_provider,
)

CORPUS = [
    ("trousers", "beige", "wide leg", "smart casual", ["beige", "navy"]),
    ("shirt", "light blue", "relaxed", "smart casual", ["beige", "navy"]),
    ("sweater", "navy", "relaxed", "smart casual", ["navy", "beige"]),
    ("cardigan", "navy", "relaxed", "smart casual", ["navy", "beige"]),
    ("polo", "navy", "regular", "smart casual", ["navy", "beige"]),
    ("t-shirt", "brown", "short sleeve", "casual", ["brown", "cream"]),
    ("shorts", "cream", "wide leg", "casual", ["brown", "cream"]),
    ("shoes", "brown", "loafer", "smart casual", ["brown", "cream"]),
]


def _context(
    category: str,
    color: str,
    cut: str,
    style: str,
    palette: list[str],
    budget: float,
) -> SearchContext:
    piece = LookPiece(
        look_id="smoke-look",
        outfit_id="smoke-outfit",
        category_raw=category,
        category=category,
        color=color,
        cut=cut,
        material=None,
        swatch=None,
        confidence=0.9,
    )
    return SearchContext(
        piece=piece,
        outfit_style=style,
        dominant_palette=palette,
        budget_available=budget,
        ship_to="FR",
        currency="EUR",
    )


def _candidate_json(candidate) -> dict[str, Any]:
    body = asdict(candidate)
    body["fetched_at"] = candidate.fetched_at.isoformat()
    body["expires_at"] = candidate.expires_at.isoformat() if candidate.expires_at else None
    return body


def run(output: Path, budget: float, limit: int, verify: bool, skip_discovery: bool) -> int:
    provider = get_product_search_provider()
    discovery: dict[str, Any] | None = None
    if isinstance(provider, ShopifyGlobalCatalogProvider) and not skip_discovery:
        try:
            discovery = provider.tools_list()
            print("MCP tools/list succeeded; schema captured in report")
        except Exception as exc:
            report = {
                "generated_at": datetime.now(UTC).isoformat(),
                "provider": type(provider).__name__,
                "budget": budget,
                "protocol_discovery": {
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
                "results": [],
                "summary": {"queries_attempted": 0, "queries_succeeded": 0},
            }
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"MCP tools/list failed: {type(exc).__name__} - {exc}")
            print(f"Report written to {output}")
            return 2

    rows: list[dict[str, Any]] = []
    search_latencies: list[float] = []
    verify_latencies: list[float] = []
    all_prices: list[float] = []

    for category, color, cut, style, palette in CORPUS:
        ctx = _context(category, color, cut, style, palette, budget)
        started = time.perf_counter()
        try:
            candidates = provider.search(ctx, limit=limit)
            search_ms = (time.perf_counter() - started) * 1000
            search_latencies.append(search_ms)
            all_prices.extend(candidate.price for candidate in candidates)
            row: dict[str, Any] = {
                "query": {"category": category, "color": color, "cut": cut, "style": style},
                "search_ms": round(search_ms, 1),
                "candidate_count": len(candidates),
                "candidates": [_candidate_json(candidate) for candidate in candidates],
            }
            if verify and candidates:
                verify_started = time.perf_counter()
                verified = provider.verify(candidates[0])
                verify_ms = (time.perf_counter() - verify_started) * 1000
                verify_latencies.append(verify_ms)
                row["verify_ms"] = round(verify_ms, 1)
                row["verified"] = _candidate_json(verified) if verified else None
                row["price_delta"] = (
                    round(verified.price - candidates[0].price, 2)
                    if verified
                    else None
                )
            rows.append(row)
            print(f"{category}/{color}: {len(candidates)} candidates in {search_ms:.0f} ms")
        except Exception as exc:  # live harness must continue per query
            rows.append(
                {
                    "query": {"category": category, "color": color, "cut": cut, "style": style},
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            print(f"{category}/{color}: ERROR {type(exc).__name__} - {exc}")

    candidates_flat = [candidate for row in rows for candidate in row.get("candidates", [])]
    successful = [row for row in rows if "error_type" not in row]
    coverage = sum(row.get("candidate_count", 0) >= 3 for row in rows) / len(rows) if rows else 0
    image_ratio = (
        sum(bool(candidate.get("image_url")) for candidate in candidates_flat) / len(candidates_flat)
        if candidates_flat
        else 0
    )
    availability_ratio = (
        sum(candidate.get("is_available") is True for candidate in candidates_flat) / len(candidates_flat)
        if candidates_flat
        else 0
    )
    median_price = statistics.median(all_prices) if all_prices else None
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": type(provider).__name__,
        "budget": budget,
        "protocol_discovery": discovery,
        "results": rows,
        "summary": {
            "queries_attempted": len(rows),
            "queries_succeeded": len(successful),
            "coverage_at_least_3": round(coverage, 3),
            "image_ratio": round(image_ratio, 3),
            "availability_ratio": round(availability_ratio, 3),
            "median_candidate_price": median_price,
            "median_price_to_budget_ratio": round(median_price / budget, 3) if median_price is not None else None,
            "search_p95_ms": round(max(search_latencies), 1) if search_latencies else None,
            "verify_p95_ms": round(max(verify_latencies), 1) if verify_latencies else None,
        },
        "gate": {
            "coverage_at_least_3_target": 0.8,
            "image_ratio_target": 0.9,
            "availability_ratio_target": 0.7,
            "search_p95_ms_target": 800,
            "verify_p95_ms_target": 500,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/product-search-smoke.json"))
    parser.add_argument("--budget", type=float, default=100.0)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--skip-discovery", action="store_true")
    args = parser.parse_args()
    return run(args.output, args.budget, args.limit, args.verify, args.skip_discovery)


if __name__ == "__main__":
    raise SystemExit(main())

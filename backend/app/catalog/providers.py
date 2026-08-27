from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx

from app.capture.models import LookPiece
from app.config import settings


@dataclass(frozen=True)
class SearchContext:
    piece: LookPiece
    outfit_style: str | None
    dominant_palette: list[str]
    budget_available: float | None
    ship_to: str = "FR"
    currency: str = "EUR"


@dataclass(frozen=True)
class ProductCandidate:
    provider: str
    external_id: str
    name: str
    price: float
    currency: str
    merchant: str
    product_url: str
    image_url: str | None = None
    checkout_url: str | None = None
    variant_id: str | None = None
    original_price: float | None = None
    shipping_price: float | None = None
    availability: str | None = None
    brand: str | None = None
    size: str | None = None
    color: str | None = None
    cut: str | None = None
    material: str | None = None
    raw_category: str | None = None
    condition: str = "new"
    fetched_at: datetime = datetime.min.replace(tzinfo=UTC)
    expires_at: datetime | None = None
    similarity: int | None = None
    purchase_score: float | None = None

    @property
    def affiliate_url(self) -> str:
        """Backward-compatible alias until Option persistence is upgraded."""
        return self.product_url


class ProductSearchProvider(Protocol):
    def search(self, ctx: SearchContext, limit: int = 5) -> list[ProductCandidate]: ...

    def verify(self, candidate: ProductCandidate) -> ProductCandidate | None: ...


class MockProductSearchProvider:
    def search(self, ctx: SearchContext, limit: int = 5) -> list[ProductCandidate]:
        now = datetime.now(UTC)
        candidates = [
            ProductCandidate(
                provider="mock",
                external_id="mock-39",
                name=f"Mock {ctx.piece.category} 39",
                price=39.99,
                currency=ctx.currency,
                merchant="Mock Basics",
                product_url="https://example.test/39",
                fetched_at=now,
                expires_at=now + timedelta(hours=24),
                similarity=82,
                purchase_score=0.72,
            ),
            ProductCandidate(
                provider="mock",
                external_id="mock-49",
                name=f"Mock {ctx.piece.category} 49",
                price=49.99,
                currency=ctx.currency,
                merchant="Mock Wardrobe",
                product_url="https://example.test/49",
                fetched_at=now,
                expires_at=now + timedelta(hours=24),
                similarity=94,
                purchase_score=0.91,
            ),
            ProductCandidate(
                provider="mock",
                external_id="mock-69",
                name=f"Mock {ctx.piece.category} 69",
                price=69.99,
                currency=ctx.currency,
                merchant="Mock Premium",
                product_url="https://example.test/69",
                fetched_at=now,
                expires_at=now + timedelta(hours=24),
                similarity=97,
                purchase_score=0.84,
            ),
        ]
        if ctx.budget_available is not None:
            within_budget = [candidate for candidate in candidates if candidate.price <= ctx.budget_available]
            if within_budget:
                candidates = within_budget
        return candidates[:limit]

    def verify(self, candidate: ProductCandidate) -> ProductCandidate | None:
        return candidate


class ShopifyGlobalCatalogProvider:
    """Experimental Shopify Global Catalog MCP adapter.

    The endpoint needs no API key, but every request must advertise a public UCP
    agent profile URL. Prices are returned in minor units and are localized via
    the request context.
    """

    endpoint = "https://catalog.shopify.com/api/ucp/mcp"

    def __init__(self, profile_url: str | None = None, client: httpx.Client | None = None) -> None:
        self.profile_url = profile_url or settings.shopify_ucp_profile_url
        if not self.profile_url:
            raise RuntimeError("SHOPIFY_UCP_PROFILE_URL is required for Shopify Global Catalog")
        self.client = client or httpx.Client(timeout=settings.product_search_timeout_seconds)

    def _call(self, tool: str, catalog: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {
                "name": tool,
                "arguments": {
                    "meta": {"ucp-agent": {"profile": self.profile_url}},
                    "catalog": catalog,
                },
            },
        }
        response = self.client.post(self.endpoint, json=payload)
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise RuntimeError(f"Shopify catalog error: {body['error']}")
        return body.get("result", {}).get("structuredContent", {})

    @staticmethod
    def _query(ctx: SearchContext) -> str:
        terms = [ctx.piece.category]
        if ctx.piece.color:
            terms.append(ctx.piece.color)
        if ctx.piece.cut:
            terms.append(ctx.piece.cut)
        if ctx.outfit_style:
            terms.append(ctx.outfit_style)
        return " ".join(dict.fromkeys(term.strip() for term in terms if term and term.strip()))

    @staticmethod
    def _minor_to_major(value: Any) -> float:
        return round(float(value or 0) / 100, 2)

    @staticmethod
    def _first_image(product: dict[str, Any]) -> str | None:
        for media in product.get("media", []):
            if media.get("type") == "image" and media.get("url"):
                return str(media["url"])
        return None

    @staticmethod
    def _attribute(product: dict[str, Any], name: str) -> str | None:
        wanted = name.lower()
        for option in product.get("options", []):
            if str(option.get("name", "")).lower() == wanted:
                values = option.get("values") or []
                if values:
                    label = values[0].get("label")
                    return str(label) if label else None
        for attribute in product.get("metadata", {}).get("attributes", []):
            if str(attribute.get("name", "")).lower() == wanted:
                value = attribute.get("value") or attribute.get("label")
                return str(value) if value else None
        return None

    def _candidate_from_product(self, product: dict[str, Any], *, fetched_at: datetime) -> ProductCandidate | None:
        variants = product.get("variants") or []
        variant = next(
            (item for item in variants if item.get("availability", {}).get("available") is True),
            variants[0] if variants else None,
        )
        price_data = (variant or {}).get("price") or product.get("price_range", {}).get("min") or {}
        amount = price_data.get("amount")
        if amount is None:
            return None
        seller = (variant or {}).get("seller") or {}
        merchant = seller.get("name") or seller.get("domain") or "Shopify merchant"
        availability_data = (variant or {}).get("availability") or {}
        categories = product.get("categories") or []
        raw_category = None
        if categories:
            raw_category = categories[0].get("value")
        condition = (variant or {}).get("condition") or ["new"]
        return ProductCandidate(
            provider="shopify_global_catalog",
            external_id=str(product.get("id", "")),
            variant_id=str(variant.get("id")) if variant and variant.get("id") else None,
            name=str(product.get("title") or "Shopify product"),
            price=self._minor_to_major(amount),
            currency=str(price_data.get("currency") or "EUR"),
            merchant=str(merchant),
            product_url=str(product.get("url") or seller.get("url") or ""),
            checkout_url=(str(variant.get("checkout_url")) if variant and variant.get("checkout_url") else None),
            image_url=self._first_image(product),
            availability=str(availability_data.get("status")) if availability_data.get("status") else None,
            size=self._attribute(product, "Size"),
            color=self._attribute(product, "Color"),
            material=self._attribute(product, "Material"),
            cut=self._attribute(product, "Style"),
            raw_category=str(raw_category) if raw_category else None,
            condition=str(condition[0]) if isinstance(condition, list) and condition else "new",
            fetched_at=fetched_at,
            expires_at=fetched_at + timedelta(hours=24),
        )

    def search(self, ctx: SearchContext, limit: int = 5) -> list[ProductCandidate]:
        filters: dict[str, Any] = {
            "ships_to": {"country": ctx.ship_to},
            "available": True,
        }
        if ctx.budget_available is not None:
            filters["price"] = {"max": max(0, round(ctx.budget_available * 100))}
        if ctx.piece.color:
            filters["attributes"] = [{"name": "Color", "values": [ctx.piece.color]}]
        intent_parts = [ctx.outfit_style or "", ", ".join(ctx.dominant_palette)]
        catalog = {
            "query": self._query(ctx),
            "filters": filters,
            "context": {
                "address_country": ctx.ship_to,
                "currency": ctx.currency,
                "intent": " · ".join(part for part in intent_parts if part),
            },
            "pagination": {"limit": limit},
        }
        content = self._call("search_catalog", catalog)
        fetched_at = datetime.now(UTC)
        candidates = [
            candidate
            for product in content.get("products", [])
            if (candidate := self._candidate_from_product(product, fetched_at=fetched_at)) is not None
        ]
        return candidates[:limit]

    def verify(self, candidate: ProductCandidate) -> ProductCandidate | None:
        catalog = {
            "id": candidate.variant_id or candidate.external_id,
            "context": {"address_country": "FR", "currency": candidate.currency},
        }
        content = self._call("get_product", catalog)
        product = content.get("product")
        if not product:
            return None
        verified = self._candidate_from_product(product, fetched_at=datetime.now(UTC))
        if verified is None or verified.availability == "out_of_stock":
            return None
        return verified


def get_product_search_provider() -> ProductSearchProvider:
    provider = settings.product_search_provider.lower()
    if provider == "shopify":
        return ShopifyGlobalCatalogProvider()
    return MockProductSearchProvider()

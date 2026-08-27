from __future__ import annotations

import json
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
    fetched_at: datetime
    image_url: str | None = None
    checkout_url: str | None = None
    variant_id: str | None = None
    original_price: float | None = None
    shipping_price: float | None = None
    availability: str | None = None
    is_available: bool | None = None
    brand: str | None = None
    size: str | None = None
    color: str | None = None
    cut: str | None = None
    material: str | None = None
    raw_category: str | None = None
    condition: str = "new"
    expires_at: datetime | None = None
    similarity: int | None = None
    purchase_score: float | None = None

    @property
    def affiliate_url(self) -> str:
        """Backward-compatible alias while the mobile still reads affiliate_url."""
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
                is_available=True,
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
                is_available=True,
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
                is_available=True,
                similarity=97,
                purchase_score=0.84,
            ),
        ]
        if ctx.budget_available is not None:
            discovery_ceiling = max(0.0, ctx.budget_available * 1.5)
            bounded = [candidate for candidate in candidates if candidate.price <= discovery_ceiling]
            if bounded:
                candidates = bounded
        return candidates[:limit]

    def verify(self, candidate: ProductCandidate) -> ProductCandidate | None:
        return candidate if candidate.is_available is not False else None


class ShopifyGlobalCatalogProvider:
    """Experimental Shopify Global Catalog MCP adapter.

    The endpoint needs no API key, but every request must advertise a public UCP
    agent profile URL. The live smoke test must discover the MCP tool schemas
    before this adapter is considered production-ready.
    """

    endpoint = "https://catalog.shopify.com/api/ucp/mcp"

    def __init__(self, profile_url: str | None = None, client: httpx.Client | None = None) -> None:
        self.profile_url = profile_url or settings.shopify_ucp_profile_url
        if not self.profile_url:
            raise RuntimeError("SHOPIFY_UCP_PROFILE_URL is required for Shopify Global Catalog")
        self.client = client or _shared_shopify_client()

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
        response = self.client.post(
            self.endpoint,
            json=payload,
            headers={"Accept": "application/json, text/event-stream"},
        )
        response.raise_for_status()
        body = _decode_mcp_response(response)
        if body.get("error"):
            raise RuntimeError(f"Shopify catalog error: {body['error']}")
        return body.get("result", {}).get("structuredContent", {})

    def tools_list(self) -> dict[str, Any]:
        """Discover live MCP schemas before trusting the experimental adapter."""
        response = self.client.post(
            self.endpoint,
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={"Accept": "application/json, text/event-stream"},
        )
        response.raise_for_status()
        return _decode_mcp_response(response)

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

    @staticmethod
    def _condition(variant: dict[str, Any]) -> str:
        condition = variant.get("condition")
        if isinstance(condition, list):
            return str(condition[0]) if condition else "new"
        if isinstance(condition, str) and condition.strip():
            return condition
        return "new"

    def _candidate_from_product(
        self,
        product: dict[str, Any],
        *,
        fetched_at: datetime,
        required_variant_id: str | None = None,
    ) -> ProductCandidate | None:
        variants = product.get("variants") or []
        if required_variant_id is not None:
            variant = next((item for item in variants if str(item.get("id")) == required_variant_id), None)
            if variant is None:
                return None
        else:
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
        available_value = availability_data.get("available")
        categories = product.get("categories") or []
        raw_category = categories[0].get("value") if categories else None
        return ProductCandidate(
            provider="shopify_global_catalog",
            external_id=str(product.get("id", "")),
            variant_id=str(variant.get("id")) if variant and variant.get("id") else None,
            name=str(product.get("title") or "Shopify product"),
            price=self._minor_to_major(amount),
            currency=str(price_data.get("currency") or "EUR"),
            merchant=str(merchant),
            product_url=str(product.get("url") or seller.get("url") or ""),
            fetched_at=fetched_at,
            checkout_url=(
                str(variant.get("checkout_url"))
                if variant and variant.get("checkout_url")
                else None
            ),
            image_url=self._first_image(product),
            availability=(
                str(availability_data.get("status"))
                if availability_data.get("status")
                else None
            ),
            is_available=available_value if isinstance(available_value, bool) else None,
            size=self._attribute(product, "Size"),
            color=self._attribute(product, "Color"),
            material=self._attribute(product, "Material"),
            cut=self._attribute(product, "Style"),
            raw_category=str(raw_category) if raw_category else None,
            condition=self._condition(variant or {}),
            expires_at=fetched_at + timedelta(hours=24),
        )

    def search(self, ctx: SearchContext, limit: int = 5) -> list[ProductCandidate]:
        filters: dict[str, Any] = {
            "ships_to": {"country": ctx.ship_to},
            "available": True,
        }
        if ctx.budget_available is not None:
            discovery_ceiling = max(0.0, ctx.budget_available * 1.5)
            filters["price"] = {"max": round(discovery_ceiling * 100)}
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
            "id": candidate.external_id,
            "context": {"address_country": "FR", "currency": candidate.currency},
        }
        content = self._call("get_product", catalog)
        product = content.get("product")
        if not product:
            return None
        verified = self._candidate_from_product(
            product,
            fetched_at=datetime.now(UTC),
            required_variant_id=candidate.variant_id,
        )
        if verified is None or verified.is_available is not True:
            return None
        return verified


_SHARED_SHOPIFY_CLIENT: httpx.Client | None = None


def _shared_shopify_client() -> httpx.Client:
    global _SHARED_SHOPIFY_CLIENT
    if _SHARED_SHOPIFY_CLIENT is None:
        _SHARED_SHOPIFY_CLIENT = httpx.Client(timeout=settings.product_search_timeout_seconds)
    return _SHARED_SHOPIFY_CLIENT


def _decode_mcp_response(response: httpx.Response) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" not in content_type:
        return response.json()
    for line in response.text.splitlines():
        if line.startswith("data:"):
            data = line.removeprefix("data:").strip()
            if data and data != "[DONE]":
                return json.loads(data)
    raise RuntimeError("MCP SSE response contained no JSON data")


def candidate_from_option(option: Any) -> ProductCandidate:
    """Rehydrate a provider candidate from persisted Option fields."""
    if option.fetched_at is None:
        raise ValueError("persisted option has no fetched_at timestamp")
    return ProductCandidate(
        provider=option.provider or "mock",
        external_id=option.external_id or option.id,
        name=option.name or "Product option",
        price=float(option.price),
        currency=option.currency or "EUR",
        merchant=option.merchant or "Unknown merchant",
        product_url=option.product_url or option.affiliate_url or "",
        fetched_at=option.fetched_at,
        image_url=option.image_url,
        checkout_url=option.checkout_url,
        variant_id=option.variant_id,
        original_price=float(option.original_price) if option.original_price is not None else None,
        shipping_price=float(option.shipping_price) if option.shipping_price is not None else None,
        availability=option.availability,
        is_available=option.is_available,
        brand=option.brand,
        size=option.size,
        color=option.color,
        cut=option.cut,
        material=option.material,
        raw_category=option.raw_category,
        condition=option.condition or "new",
        expires_at=option.expires_at,
        similarity=option.similarity,
        purchase_score=float(option.purchase_score) if option.purchase_score is not None else None,
    )


def get_product_search_provider(provider_name: str | None = None) -> ProductSearchProvider:
    provider = (provider_name or settings.product_search_provider).lower()
    if provider in {"shopify", "shopify_global_catalog"}:
        return ShopifyGlobalCatalogProvider()
    return MockProductSearchProvider()

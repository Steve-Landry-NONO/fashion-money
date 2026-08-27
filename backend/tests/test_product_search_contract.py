import json

import httpx

from app.capture.models import LookPiece
from app.catalog.providers import MockProductSearchProvider, SearchContext, ShopifyGlobalCatalogProvider


def _ctx(*, budget: float = 100.0) -> SearchContext:
    piece = LookPiece(
        look_id="look-1",
        outfit_id="outfit-1",
        category_raw="pants",
        category="trousers",
        color="beige",
        cut="wide leg",
        material=None,
        swatch=None,
        confidence=0.9,
    )
    return SearchContext(
        piece=piece,
        outfit_style="smart casual",
        dominant_palette=["beige", "navy"],
        budget_available=budget,
        ship_to="FR",
        currency="EUR",
    )


def _shopify_product(
    price: int = 4999,
    *,
    variant_id: str = "gid://shopify/ProductVariant/variant-1",
    available: bool = True,
    condition: object = None,
) -> dict:
    return {
        "id": "gid://shopify/p/product-1",
        "title": "Wide leg trousers",
        "url": "https://merchant.example/products/trousers",
        "price_range": {
            "min": {"amount": price, "currency": "EUR"},
            "max": {"amount": price, "currency": "EUR"},
        },
        "media": [{"type": "image", "url": "https://cdn.example/trousers.jpg"}],
        "categories": [{"value": "Apparel > Pants", "taxonomy": "merchant"}],
        "options": [
            {"name": "Color", "values": [{"label": "Beige"}]},
            {"name": "Size", "values": [{"label": "M"}]},
        ],
        "variants": [
            {
                "id": variant_id,
                "price": {"amount": price, "currency": "EUR"},
                "checkout_url": "https://merchant.example/cart/variant-1:1",
                "availability": {
                    "available": available,
                    "status": "in_stock" if available else "sold_out",
                },
                "condition": ["new"] if condition is None else condition,
                "seller": {
                    "name": "Merchant FR",
                    "url": "https://merchant.example",
                },
            }
        ],
    }


def test_shopify_search_uses_discovery_ceiling_and_fr_context() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.update(body)
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"structuredContent": {"products": [_shopify_product()]}},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = ShopifyGlobalCatalogProvider(
        profile_url="https://fashion.money/ucp/profile.json",
        client=client,
    )

    candidates = provider.search(_ctx(), limit=3)

    catalog = seen["params"]["arguments"]["catalog"]
    meta = seen["params"]["arguments"]["meta"]
    assert seen["params"]["name"] == "search_catalog"
    assert meta["ucp-agent"]["profile"] == "https://fashion.money/ucp/profile.json"
    assert catalog["filters"]["price"]["max"] == 15000
    assert catalog["filters"]["ships_to"] == {"country": "FR"}
    assert catalog["context"]["address_country"] == "FR"
    assert catalog["context"]["currency"] == "EUR"
    assert "smart casual" in catalog["query"]
    assert len(candidates) == 1


def test_mock_keeps_an_over_budget_candidate_for_decision_engine() -> None:
    candidates = MockProductSearchProvider().search(_ctx(budget=50.0), limit=5)
    assert any(candidate.price > 50.0 for candidate in candidates)


def test_shopify_candidate_keeps_product_and_checkout_urls_separate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"structuredContent": {"products": [_shopify_product()]}},
            },
        )

    provider = ShopifyGlobalCatalogProvider(
        profile_url="https://fashion.money/ucp/profile.json",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    candidate = provider.search(_ctx(), limit=1)[0]

    assert candidate.price == 49.99
    assert candidate.currency == "EUR"
    assert candidate.product_url == "https://merchant.example/products/trousers"
    assert candidate.checkout_url == "https://merchant.example/cart/variant-1:1"
    assert candidate.variant_id == "gid://shopify/ProductVariant/variant-1"
    assert candidate.availability == "in_stock"
    assert candidate.is_available is True
    assert candidate.color == "Beige"
    assert candidate.size == "M"


def test_shopify_verify_revalidates_current_variant_price() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        tool = body["params"]["name"]
        calls.append(tool)
        if tool == "search_catalog":
            content = {"products": [_shopify_product()]}
        else:
            content = {"product": _shopify_product(5999)}
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": {"structuredContent": content}},
        )

    provider = ShopifyGlobalCatalogProvider(
        profile_url="https://fashion.money/ucp/profile.json",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    discovered = provider.search(_ctx(), limit=1)[0]
    verified = provider.verify(discovered)

    assert calls == ["search_catalog", "get_product"]
    assert discovered.price == 49.99
    assert verified is not None
    assert verified.price == 59.99


def test_shopify_verify_fails_closed_if_exact_variant_is_gone() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["params"]["name"] == "search_catalog":
            content = {"products": [_shopify_product()]}
        else:
            content = {
                "product": _shopify_product(
                    variant_id="gid://shopify/ProductVariant/variant-2",
                )
            }
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": {"structuredContent": content}},
        )

    provider = ShopifyGlobalCatalogProvider(
        profile_url="https://fashion.money/ucp/profile.json",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    discovered = provider.search(_ctx(), limit=1)[0]
    assert provider.verify(discovered) is None


def test_shopify_verify_fails_closed_when_available_is_false() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["params"]["name"] == "search_catalog":
            content = {"products": [_shopify_product()]}
        else:
            content = {"product": _shopify_product(available=False)}
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": {"structuredContent": content}},
        )

    provider = ShopifyGlobalCatalogProvider(
        profile_url="https://fashion.money/ucp/profile.json",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    discovered = provider.search(_ctx(), limit=1)[0]
    assert provider.verify(discovered) is None


def test_shopify_preserves_string_condition() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "structuredContent": {
                        "products": [_shopify_product(condition="used")],
                    }
                },
            },
        )

    provider = ShopifyGlobalCatalogProvider(
        profile_url="https://fashion.money/ucp/profile.json",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    candidate = provider.search(_ctx(), limit=1)[0]
    assert candidate.condition == "used"

from dataclasses import dataclass
from typing import Protocol

from app.capture.models import LookPiece


@dataclass(frozen=True)
class ProductCandidate:
    price: float
    merchant: str
    affiliate_url: str
    similarity: int
    purchase_score: float


class ProductSearchProvider(Protocol):
    def search(self, piece: LookPiece, budget: float | None = None, ship_to: str = "FR") -> list[ProductCandidate]: ...


class MockProductSearchProvider:
    def search(self, piece: LookPiece, budget: float | None = None, ship_to: str = "FR") -> list[ProductCandidate]:
        return [
            ProductCandidate(39.99, "Mock Basics", "https://example.test/39", 82, 0.72),
            ProductCandidate(49.99, "Mock Wardrobe", "https://example.test/49", 94, 0.91),
            ProductCandidate(69.99, "Mock Premium", "https://example.test/69", 97, 0.84),
        ]


def get_product_search_provider() -> ProductSearchProvider:
    return MockProductSearchProvider()

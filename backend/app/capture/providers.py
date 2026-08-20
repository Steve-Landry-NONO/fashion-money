from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DecomposedPiece:
    category: str
    color: str | None = None
    cut: str | None = None
    material: str | None = None
    swatch: str | None = None


@dataclass(frozen=True)
class DecomposedLook:
    style: str
    pieces: list[DecomposedPiece]


class DecompositionProvider(Protocol):
    def decompose(self, image_ref: str | None = None) -> DecomposedLook: ...


class MockDecompositionProvider:
    """VS-07 mock: deterministic version of the v0.2 demo look."""

    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        return DecomposedLook(
            style="Casual chic · palette neutre",
            pieces=[
                DecomposedPiece("t-shirt", "white", "regular", "cotton", "#F1F0EA"),
                DecomposedPiece("trousers", "black", "straight", "cotton", "#24252B"),
                DecomposedPiece("sneakers", "white", "low-top", "leather", "#ECECE7"),
                DecomposedPiece("overshirt", "beige", "regular", "cotton", "#C9B79C"),
            ],
        )


def get_decomposition_provider() -> DecompositionProvider:
    return MockDecompositionProvider()

import base64
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, Field

from app.capture.storage import ImageStorage, get_image_storage
from app.config import settings


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
    """Deterministic fallback used by tests and local development."""

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


class VisionPiece(BaseModel):
    category: str = Field(description="Generic garment category in lowercase English")
    color: str | None = None
    cut: str | None = None
    material: str | None = None
    swatch: str | None = Field(default=None, description="Approximate visible color as #RRGGBB")


class VisionLook(BaseModel):
    style: str
    pieces: list[VisionPiece]


class OpenAIDecompositionProvider:
    """Real multimodal adapter. Image bytes stay private in our object store."""

    def __init__(self, storage: ImageStorage | None = None, client: OpenAI | None = None) -> None:
        if not settings.openai_api_key and client is None:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI vision provider")
        self.storage = storage or get_image_storage()
        self.client = client or OpenAI(api_key=settings.openai_api_key)

    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        if not image_ref:
            raise ValueError("image_ref is required for real vision analysis")
        image = self.storage.get(image_ref)
        encoded = base64.b64encode(image.data).decode("ascii")
        data_url = f"data:{image.content_type};base64,{encoded}"
        response = self.client.responses.parse(
            model=settings.vision_model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Analyze this fashion inspiration image. Return only visible wearable pieces "
                                "that materially define the outfit. Use generic categories rather than brands. "
                                "Describe the overall style briefly. Infer material/cut only when visually plausible."
                            ),
                        },
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            text_format=VisionLook,
        )
        parsed = response.output_parsed
        if parsed is None or not parsed.pieces:
            raise ValueError("vision provider returned no wearable pieces")
        return DecomposedLook(
            style=parsed.style,
            pieces=[
                DecomposedPiece(
                    category=p.category.strip().lower(),
                    color=p.color,
                    cut=p.cut,
                    material=p.material,
                    swatch=p.swatch,
                )
                for p in parsed.pieces
            ],
        )


def get_decomposition_provider(storage: ImageStorage | None = None) -> DecompositionProvider:
    if settings.decomposition_provider.lower() == "openai":
        return OpenAIDecompositionProvider(storage=storage)
    return MockDecompositionProvider()

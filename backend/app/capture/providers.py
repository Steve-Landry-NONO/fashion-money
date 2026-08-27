import base64
from dataclasses import dataclass
from typing import Any, Protocol

from openai import BadRequestError, OpenAI
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


def _to_decomposed_look(parsed: VisionLook) -> DecomposedLook:
    if not parsed.pieces:
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


def _image_data_url(storage: ImageStorage, image_ref: str | None) -> str:
    if not image_ref:
        raise ValueError("image_ref is required for real vision analysis")
    image = storage.get(image_ref)
    encoded = base64.b64encode(image.data).decode("ascii")
    return f"data:{image.content_type};base64,{encoded}"


VISION_PROMPT = (
    "Analyze this fashion inspiration image and return a JSON object with exactly two top-level keys: "
    '"style" and "pieces". "pieces" must be an array of visible wearable items. Each piece must contain '
    '"category", "color", "cut", "material", and "swatch". Use generic lowercase English categories rather '
    "than brands. Describe the overall style briefly. Infer material and cut only when visually plausible; "
    "otherwise use null. swatch should be an approximate visible #RRGGBB color or null. Return JSON only."
)


class OpenAIDecompositionProvider:
    """Real OpenAI multimodal adapter. Image bytes stay private in our object store."""

    def __init__(self, storage: ImageStorage | None = None, client: OpenAI | None = None) -> None:
        if not settings.openai_api_key and client is None:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI vision provider")
        self.storage = storage or get_image_storage()
        self.client = client or OpenAI(api_key=settings.openai_api_key)

    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        data_url = _image_data_url(self.storage, image_ref)
        input_payload: list[Any] = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": VISION_PROMPT},
                    {"type": "input_image", "image_url": data_url},
                ],
            }
        ]
        response = self.client.responses.parse(
            model=settings.vision_model,
            input=input_payload,
            text_format=VisionLook,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("vision provider returned no structured output")
        return _to_decomposed_look(parsed)


class GroqDecompositionProvider:
    """Groq vision adapter using its OpenAI-compatible Chat Completions API."""

    def __init__(self, storage: ImageStorage | None = None, client: OpenAI | None = None) -> None:
        if not settings.groq_api_key and client is None:
            raise RuntimeError("GROQ_API_KEY is required for the Groq vision provider")
        self.storage = storage or get_image_storage()
        self.client = client or OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )

    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        data_url = _image_data_url(self.storage, image_ref)
        messages: list[Any] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]

        last_error: BadRequestError | None = None
        for _ in range(2):
            try:
                completion = self.client.chat.completions.create(
                    model=settings.vision_model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_completion_tokens=3072,
                )
                content = completion.choices[0].message.content
                if not content:
                    raise ValueError("Groq vision provider returned empty output")
                parsed = VisionLook.model_validate_json(content)
                return _to_decomposed_look(parsed)
            except BadRequestError as exc:
                body = exc.body if isinstance(exc.body, dict) else {}
                error = body.get("error", {}) if isinstance(body, dict) else {}
                if not isinstance(error, dict) or error.get("code") != "json_validate_failed":
                    raise
                last_error = exc

        if last_error is not None:
            raise last_error
        raise RuntimeError("Groq vision provider failed without returning an error")


def get_decomposition_provider(storage: ImageStorage | None = None) -> DecompositionProvider:
    provider = settings.decomposition_provider.lower()
    if provider == "openai":
        return OpenAIDecompositionProvider(storage=storage)
    if provider == "groq":
        return GroqDecompositionProvider(storage=storage)
    return MockDecompositionProvider()
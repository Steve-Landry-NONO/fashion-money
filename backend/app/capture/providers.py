import base64
from dataclasses import dataclass
from typing import Any, Protocol

from openai import BadRequestError, OpenAI
from pydantic import BaseModel, Field, ValidationError

from app.capture.storage import ImageStorage, get_image_storage
from app.config import settings

CATEGORY_ALIASES = {
    "pants": "trousers",
    "slacks": "trousers",
    "polo shirt": "polo",
    "tee": "t-shirt",
    "t shirt": "t-shirt",
    "loafer": "shoes",
    "loafers": "shoes",
    "penny loafer": "shoes",
    "tassel loafer": "shoes",
    "sneaker": "sneakers",
}


def normalize_category(value: str) -> str:
    raw = value.strip().lower()
    return CATEGORY_ALIASES.get(raw, raw)


@dataclass(frozen=True)
class DecomposedPiece:
    category_raw: str
    category: str
    color: str | None = None
    cut: str | None = None
    material: str | None = None
    swatch: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class DecomposedOutfit:
    style: str
    pieces: list[DecomposedPiece]


@dataclass(frozen=True)
class DecomposedLook:
    image_type: str
    style: str
    dominant_palette: list[str]
    outfits: list[DecomposedOutfit]
    representative_outfit_index: int

    @property
    def pieces(self) -> list[DecomposedPiece]:
        return self.outfits[self.representative_outfit_index].pieces


class DecompositionProvider(Protocol):
    def decompose(self, image_ref: str | None = None) -> DecomposedLook: ...


class MockDecompositionProvider:
    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        pieces = [
            DecomposedPiece("t-shirt", "t-shirt", "white", "regular", "cotton", "#F1F0EA", 0.95),
            DecomposedPiece("trousers", "trousers", "black", "straight", "cotton", "#24252B", 0.95),
            DecomposedPiece("sneakers", "sneakers", "white", "low-top", "leather", "#ECECE7", 0.95),
            DecomposedPiece("overshirt", "overshirt", "beige", "regular", "cotton", "#C9B79C", 0.9),
        ]
        return DecomposedLook(
            image_type="single_outfit",
            style="Casual chic · palette neutre",
            dominant_palette=["white", "black", "beige"],
            outfits=[DecomposedOutfit(style="Casual chic", pieces=pieces)],
            representative_outfit_index=0,
        )


class VisionPiece(BaseModel):
    category: str = Field(description="Raw generic garment category in lowercase English")
    color: str | None = None
    cut: str | None = None
    material: str | None = None
    swatch: str | None = Field(default=None, description="Approximate visible color as #RRGGBB")
    confidence: float | None = Field(default=None, ge=0, le=1)


class VisionOutfit(BaseModel):
    style: str
    pieces: list[VisionPiece]


class VisionLook(BaseModel):
    image_type: str = Field(description="single_outfit or collage")
    style: str
    dominant_palette: list[str]
    outfits: list[VisionOutfit]
    representative_outfit_index: int = 0


def _choose_representative_index(outfits: list[DecomposedOutfit], requested_index: int) -> int:
    """Never auto-select a one-piece ghost outfit when a richer outfit exists."""
    requested = min(max(requested_index, 0), len(outfits) - 1)
    if len(outfits[requested].pieces) > 1:
        return requested
    richer = [index for index, outfit in enumerate(outfits) if len(outfit.pieces) > 1]
    if not richer:
        return requested
    return max(richer, key=lambda index: len(outfits[index].pieces))


def _to_decomposed_look(parsed: VisionLook) -> DecomposedLook:
    if not parsed.outfits:
        raise ValueError("vision provider returned no outfits")
    outfits: list[DecomposedOutfit] = []
    for outfit in parsed.outfits:
        if not outfit.pieces:
            continue
        pieces = [
            DecomposedPiece(
                category_raw=p.category.strip().lower(),
                category=normalize_category(p.category),
                color=p.color,
                cut=p.cut,
                material=p.material,
                swatch=p.swatch,
                confidence=p.confidence,
            )
            for p in outfit.pieces
        ]
        outfits.append(DecomposedOutfit(style=outfit.style, pieces=pieces))
    if not outfits:
        raise ValueError("vision provider returned no wearable pieces")
    index = _choose_representative_index(outfits, parsed.representative_outfit_index)
    return DecomposedLook(
        image_type="collage" if parsed.image_type.lower() == "collage" or len(outfits) > 1 else "single_outfit",
        style=parsed.style,
        dominant_palette=parsed.dominant_palette,
        outfits=outfits,
        representative_outfit_index=index,
    )


def _image_data_url(storage: ImageStorage, image_ref: str | None) -> str:
    if not image_ref:
        raise ValueError("image_ref is required for real vision analysis")
    image = storage.get(image_ref)
    encoded = base64.b64encode(image.data).decode("ascii")
    return f"data:{image.content_type};base64,{encoded}"


VISION_PROMPT = (
    "Analyze this fashion image and output ONE valid JSON object only. First count distinct visible people/looks. "
    "If there is more than one, image_type is collage and create exactly one outfit per person/look. Never merge "
    "people and never split one person into multiple outfits. Order outfits left-to-right then top-to-bottom. "
    "Required shape: image_type, style, dominant_palette, outfits, representative_outfit_index. Each outfit has "
    "style and pieces. Each piece has category, color, cut, material, swatch, confidence. Use generic lowercase "
    "English garment categories. Use null when cut, material, or swatch is uncertain; do not guess fabric. "
    "confidence is 0 to 1. representative_outfit_index defaults to 0. No markdown or extra text."
)

REPAIR_PROMPT = (
    "Return only compact valid JSON for this fashion image. For every visible person, create one outfit and keep "
    "all of that person's visible garments together. Required top-level keys: image_type, style, dominant_palette, "
    "outfits, representative_outfit_index. Each outfit: style, pieces. Each piece: category, color, cut, material, "
    "swatch, confidence. Unknown optional attributes must be null. No prose or markdown."
)

MINIMAL_REPAIR_PROMPT = (
    "JSON only. Keys: image_type, style, dominant_palette, outfits, representative_outfit_index. One outfit per "
    "visible person. Each outfit has style and pieces; each piece has category, color, cut, material, swatch, "
    "confidence. Use null when unsure. Do not output explanations."
)


class OpenAIDecompositionProvider:
    def __init__(self, storage: ImageStorage | None = None, client: OpenAI | None = None) -> None:
        if not settings.openai_api_key and client is None:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI vision provider")
        self.storage = storage or get_image_storage()
        self.client = client or OpenAI(api_key=settings.openai_api_key)

    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        data_url = _image_data_url(self.storage, image_ref)
        input_payload: Any = [
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
    def __init__(self, storage: ImageStorage | None = None, client: OpenAI | None = None) -> None:
        if not settings.groq_api_key and client is None:
            raise RuntimeError("GROQ_API_KEY is required for the Groq vision provider")
        self.storage = storage or get_image_storage()
        self.client = client or OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)

    def _request(self, data_url: str, prompt: str) -> DecomposedLook:
        messages: list[Any] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]
        completion = self.client.chat.completions.create(
            model=settings.vision_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
            max_completion_tokens=4096,
            extra_body={"reasoning_format": "hidden"},
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Groq vision provider returned empty output")
        return _to_decomposed_look(VisionLook.model_validate_json(content))

    def decompose(self, image_ref: str | None = None) -> DecomposedLook:
        data_url = _image_data_url(self.storage, image_ref)
        last_error: Exception | None = None
        # Deterministic calls are still useful when the prompt changes; never replay the exact same request.
        for prompt in (VISION_PROMPT, REPAIR_PROMPT, MINIMAL_REPAIR_PROMPT):
            try:
                return self._request(data_url, prompt)
            except BadRequestError as exc:
                body = exc.body if isinstance(exc.body, dict) else {}
                error = body.get("error", {}) if isinstance(body, dict) else {}
                code = error.get("code") if isinstance(error, dict) else None
                if code != "json_validate_failed":
                    raise
                last_error = exc
            except ValidationError as exc:
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

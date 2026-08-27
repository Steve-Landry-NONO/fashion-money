import base64
import json
from dataclasses import dataclass
from typing import Any, Protocol

from openai import BadRequestError, OpenAI
from pydantic import BaseModel, Field

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


def _to_decomposed_look(parsed: VisionLook) -> DecomposedLook:
    if not parsed.outfits:
        raise ValueError("vision provider returned no outfits")
    index = min(max(parsed.representative_outfit_index, 0), len(parsed.outfits) - 1)
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
    index = min(index, len(outfits) - 1)
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
    "Analyze this fashion inspiration image conservatively. Detect every distinct visible person/look before "
    "describing garments. If multiple people or separate look panels are visible, image_type MUST be collage and "
    "outfits MUST contain exactly one entry per distinct visible person/look. Never merge two people, never split "
    "one person into multiple outfits, and never create an outfit for a garment detail that belongs to another "
    "person. Order outfits left-to-right, then top-to-bottom. Include only garments/accessories visibly worn by "
    "that person. Return JSON only with exactly these top-level keys: image_type, style, dominant_palette, outfits, "
    "representative_outfit_index. image_type is single_outfit or collage. style is a short generic style label. "
    "dominant_palette is an array of short color names. Each outfit has exactly style and pieces. Each piece has "
    "exactly category, color, cut, material, swatch, confidence. category is a generic lowercase English garment "
    "category with no brand. color may be null only if unclear. cut, material and swatch MUST be null when the "
    "pixels do not support a reliable inference; never infer fabric merely from garment type. confidence is a "
    "number from 0 to 1 for the visible attribute extraction. representative_outfit_index is 0 unless one outfit "
    "is clearly dominant. Do not add markdown, explanations, comments, trailing text, or additional JSON keys."
)

GROQ_JSON_SCHEMA: dict[str, Any] = {
    "name": "fashion_vision_look",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "image_type": {"type": "string", "enum": ["single_outfit", "collage"]},
            "style": {"type": "string"},
            "dominant_palette": {"type": "array", "items": {"type": "string"}},
            "outfits": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "style": {"type": "string"},
                        "pieces": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "category": {"type": "string"},
                                    "color": {"type": ["string", "null"]},
                                    "cut": {"type": ["string", "null"]},
                                    "material": {"type": ["string", "null"]},
                                    "swatch": {"type": ["string", "null"]},
                                    "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                                },
                                "required": ["category", "color", "cut", "material", "swatch", "confidence"],
                            },
                        },
                    },
                    "required": ["style", "pieces"],
                },
            },
            "representative_outfit_index": {"type": "integer", "minimum": 0},
        },
        "required": ["image_type", "style", "dominant_palette", "outfits", "representative_outfit_index"],
    },
}


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

    def _request(self, messages: list[Any], response_format: dict[str, Any]) -> DecomposedLook:
        completion = self.client.chat.completions.create(
            model=settings.vision_model,
            messages=messages,
            response_format=response_format,
            temperature=0,
            max_completion_tokens=4096,
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Groq vision provider returned empty output")
        return _to_decomposed_look(VisionLook.model_validate_json(content))

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
        formats: list[dict[str, Any]] = [
            {"type": "json_schema", "json_schema": GROQ_JSON_SCHEMA},
            {"type": "json_object"},
            {"type": "json_object"},
        ]
        last_error: BadRequestError | None = None
        for attempt, response_format in enumerate(formats):
            try:
                return self._request(messages, response_format)
            except BadRequestError as exc:
                body = exc.body if isinstance(exc.body, dict) else {}
                error = body.get("error", {}) if isinstance(body, dict) else {}
                code = error.get("code") if isinstance(error, dict) else None
                if code not in {"json_validate_failed", "invalid_request_error"}:
                    raise
                last_error = exc
                if attempt == 0:
                    messages[0]["content"][0]["text"] = VISION_PROMPT + " Follow the JSON schema exactly."
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

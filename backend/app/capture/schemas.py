from pydantic import BaseModel, Field


class CaptureIn(BaseModel):
    image_ref: str | None = None


class PieceOut(BaseModel):
    id: str
    category_raw: str | None = None
    category: str
    color: str | None
    cut: str | None
    material: str | None
    swatch: str | None
    confidence: float | None = None
    owned_pct: int = 0
    is_owned: bool = False
    match_reason: str | None = None


class OutfitOut(BaseModel):
    id: str
    position: int
    style: str | None
    is_representative: bool
    pieces: list[PieceOut]


class CaptureOut(BaseModel):
    capture_id: str
    look_id: str
    status: str


class LookOut(BaseModel):
    id: str
    style: str | None
    image_type: str = "single_outfit"
    dominant_palette: list[str] = Field(default_factory=list)
    representative_outfit_index: int = 0
    outfits: list[OutfitOut] = Field(default_factory=list)
    # Kept for the current mobile client: these are only the representative outfit pieces.
    pieces: list[PieceOut]
    score_look: int

from pydantic import BaseModel


class CaptureIn(BaseModel):
    image_ref: str | None = None


class PieceOut(BaseModel):
    id: str
    category: str
    color: str | None
    cut: str | None
    material: str | None
    swatch: str | None
    owned_pct: int = 0
    is_owned: bool = False
    match_reason: str | None = None


class CaptureOut(BaseModel):
    capture_id: str
    look_id: str
    status: str


class LookOut(BaseModel):
    id: str
    style: str | None
    pieces: list[PieceOut]
    score_look: int

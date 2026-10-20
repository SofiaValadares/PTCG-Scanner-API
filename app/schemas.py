from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool
    device: str
    detector: str
    roi: str
    catalog_cards: int
    catalog_langs: list[str]


class MatchOut(BaseModel):
    name: str
    number: str
    set_id: str
    set_name: str
    rarity: str = ""
    lang: str = ""
    score: float


class RoiBandOut(BaseModel):
    source: str
    conf: float
    ocr_conf: float = 0.0
    text: str = ""


class OcrOut(BaseModel):
    name: str = ""
    number: str = ""
    collection: str = ""


class CardOut(BaseModel):
    index: int
    det_conf: float
    orient_deg: int
    quad: list[list[float]] = Field(default_factory=list)
    ocr: OcrOut
    roi: dict[str, RoiBandOut] = Field(default_factory=dict)
    match: MatchOut | None = None
    matches: list[MatchOut] = Field(default_factory=list)
    crop_jpeg_base64: str | None = None


class ImageOut(BaseModel):
    filename: str
    width: int
    height: int
    card_count: int
    cards: list[CardOut] = Field(default_factory=list)
    error: str | None = None


class ScanResponse(BaseModel):
    images: list[ImageOut]
    device: str
    elapsed_ms: float
    image_count: int
    card_count: int

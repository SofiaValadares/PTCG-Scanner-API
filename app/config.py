from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for folder in [here.parent, *here.parents]:
        if (folder / "app" / "main.py").is_file() and (folder / "models").is_dir():
            return folder
    return Path.cwd()


ROOT = repo_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "*"

    detector_weights: Path = ROOT / "models" / "obb-v6.pt"
    roi_weights: Path = ROOT / "models" / "ocr-roi-v3.pt"
    catalog_dir: Path = ROOT / "data" / "catalog"
    catalog_lang: str = "en"

    device: str = "auto"
    card_conf: float = 0.8
    roi_conf: float = 0.4

    max_files: int = 20
    max_file_bytes: int = 12 * 1024 * 1024
    include_crops_default: bool = False
    top_n: int = 3
    jpeg_quality: int = 75
    api_key: str = ""

    @field_validator("detector_weights", "roi_weights", "catalog_dir", mode="before")
    @classmethod
    def _resolve_repo_path(cls, value):
        path = Path(value)
        return path if path.is_absolute() else ROOT / path

    def resolve_device(self) -> str | int:
        value = (self.device or "auto").strip().lower()
        if value in {"auto", ""}:
            try:
                import torch

                return 0 if torch.cuda.is_available() else "cpu"
            except Exception:
                return "cpu"
        if value.isdigit():
            return int(value)
        return value


settings = Settings()

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas import HealthResponse, ScanResponse
from ptcg_api.engine import Scanner

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _scanner() -> Scanner:
    scanner = getattr(app.state, "scanner", None)
    if scanner is None:
        raise HTTPException(status_code=503, detail="Models are still loading.")
    return scanner


def check_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = (settings.api_key or "").strip()
    if not expected:
        return
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.scanner = Scanner(
        detector_weights=settings.detector_weights,
        roi_weights=settings.roi_weights,
        catalog_dir=settings.catalog_dir,
        catalog_lang=settings.catalog_lang,
        device=settings.resolve_device(),
        card_conf=settings.card_conf,
        roi_conf=settings.roi_conf,
        top_n=settings.top_n,
        jpeg_quality=settings.jpeg_quality,
    )
    yield
    application.state.scanner = None


app = FastAPI(
    title="PTCG Scanner API",
    description=(
        "Detect Pokémon TCG cards in one or more photos, warp each to 63×88 mm, "
        "read name / number / set, and match against the catalog. "
        "Inference-only — training lives in the PTCG Scanner thesis repo."
    ),
    version="0.1.0",
    lifespan=lifespan,
    license_info={"name": "CC BY-NC 4.0", "url": "https://creativecommons.org/licenses/by-nc/4.0/"},
)

origins = [part.strip() for part in settings.cors_origins.split(",") if part.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if origins == ["*"] else origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "PTCG Scanner API",
        "docs": "/docs",
        "health": "/health",
        "scan": "POST /v1/scan",
    }


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health(scanner: Scanner = Depends(_scanner)):
    info = scanner.info()
    return HealthResponse(
        ok=True,
        device=info["device"],
        detector=info["detector"],
        roi=info["roi"],
        catalog_cards=info["catalog_cards"],
        catalog_langs=info["catalog_langs"],
    )


@app.get("/v1/info", tags=["meta"])
def info(scanner: Scanner = Depends(_scanner), _: None = Depends(check_api_key)):
    return scanner.info()


@app.post("/v1/scan", response_model=ScanResponse, tags=["scan"])
async def scan(
    images: list[UploadFile] | None = File(
        default=None,
        description="One or more photos. Repeat the field: -F images=@a.jpg -F images=@b.jpg",
    ),
    image: UploadFile | None = File(
        default=None,
        description="Single photo (same as sending one file in `images`).",
    ),
    include_crops: bool = Query(
        default=None,
        description="If true, each card includes crop_jpeg_base64.",
    ),
    set_id: str = Query(default="", description="Optional PkmnCards setId to bias catalog match."),
    top_n: int | None = Query(default=None, ge=1, le=10),
    scanner: Scanner = Depends(_scanner),
    _: None = Depends(check_api_key),
):
    uploads: list[UploadFile] = []
    if image is not None:
        uploads.append(image)
    if images:
        uploads.extend(images)
    uploads = [item for item in uploads if item is not None and item.filename]
    if not uploads:
        raise HTTPException(
            status_code=400,
            detail="Send one file as `image` or one/many as `images`.",
        )
    if len(uploads) > settings.max_files:
        raise HTTPException(
            status_code=400,
            detail=f"At most {settings.max_files} images per request.",
        )

    want_crops = settings.include_crops_default if include_crops is None else include_crops
    started = time.perf_counter()
    results = []
    for upload in uploads:
        suffix = ""
        if upload.filename and "." in upload.filename:
            suffix = "." + upload.filename.rsplit(".", 1)[-1].lower()
        if suffix and suffix not in ALLOWED_SUFFIXES:
            results.append(
                {
                    "filename": upload.filename or "upload",
                    "width": 0,
                    "height": 0,
                    "card_count": 0,
                    "cards": [],
                    "error": f"Unsupported type {suffix}",
                }
            )
            continue
        data = await upload.read()
        if len(data) > settings.max_file_bytes:
            results.append(
                {
                    "filename": upload.filename or "upload",
                    "width": 0,
                    "height": 0,
                    "card_count": 0,
                    "cards": [],
                    "error": f"File larger than {settings.max_file_bytes} bytes",
                }
            )
            continue
        results.append(
            scanner.scan_bytes(
                data,
                upload.filename or "upload",
                include_crops=want_crops,
                set_id=set_id,
                top_n=top_n,
            )
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 1)
    return ScanResponse(
        images=results,
        device=str(scanner.device),
        elapsed_ms=elapsed_ms,
        image_count=len(results),
        card_count=sum(item.get("card_count", 0) for item in results),
    )


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()

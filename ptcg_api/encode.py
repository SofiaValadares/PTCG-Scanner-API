from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image


def decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None or getattr(bgr, "size", 0) == 0:
        raise ValueError("Could not decode image (use JPEG, PNG, WebP, or BMP).")
    return bgr


def bgr_to_jpeg_b64(bgr: np.ndarray, quality: int = 75) -> str:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="JPEG", quality=int(quality), optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def quad_to_list(quad: np.ndarray) -> list[list[float]]:
    pts = np.asarray(quad, dtype=np.float32).reshape(-1, 2)
    return [[round(float(x), 2), round(float(y), 2)] for x, y in pts]


def quad_norm(quad: np.ndarray | None, width: int, height: int) -> list[list[float]]:
    if quad is None:
        return []
    w = max(float(width), 1.0)
    h = max(float(height), 1.0)
    pts = np.asarray(quad, dtype=np.float32).reshape(-1, 2)
    return [[round(float(x) / w, 4), round(float(y) / h, 4)] for x, y in pts]

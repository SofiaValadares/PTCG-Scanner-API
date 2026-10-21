from __future__ import annotations

import threading
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from ptcg_api.catalog import has_collector_number, load_catalogs, match_catalog
from ptcg_api.encode import bgr_to_jpeg_b64, decode_image, quad_norm, quad_to_list
from ptcg_api.paths import ROOT, SRC  # noqa: F401
from ptcg_api.roi import orient_printed_up

from cropper.rectify import crop_result
from ocr.read_card import create_reader, read_card


def imgsz_for_weights(weights: Path) -> int:
    name = weights.name.lower()
    if "v3" in name or "v2" in name or "v1" in name:
        return 800
    return 960


def sort_crops(crops, image_shape) -> list:
    h = max(int(image_shape[0]), 1)
    row_h = max(h / 4.0, 40.0)

    def key(card):
        cy = float(card.quad[:, 1].mean())
        cx = float(card.quad[:, 0].mean())
        return (int(cy / row_h), cx)

    return sorted(crops, key=key)


def card_to_bgr(card) -> np.ndarray:
    img = card.image
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


class Scanner:
    def __init__(
        self,
        detector_weights: Path,
        roi_weights: Path,
        catalog_dir: Path,
        catalog_lang: str = "en",
        device: str | int = "cpu",
        card_conf: float = 0.8,
        roi_conf: float = 0.4,
        top_n: int = 3,
        jpeg_quality: int = 75,
    ):
        if not Path(detector_weights).is_file():
            raise FileNotFoundError(f"Detector weights not found: {detector_weights}")
        if not Path(roi_weights).is_file():
            raise FileNotFoundError(f"ROI weights not found: {roi_weights}")
        self.detector_weights = Path(detector_weights)
        self.roi_weights = Path(roi_weights)
        self.device = device
        self.card_conf = card_conf
        self.roi_conf = roi_conf
        self.top_n = top_n
        self.jpeg_quality = jpeg_quality
        self.obb_imgsz = imgsz_for_weights(self.detector_weights)
        self.card_model = YOLO(str(self.detector_weights))
        self.roi_model = YOLO(str(self.roi_weights))
        self.reader = create_reader(catalog_dir)
        self.catalog = load_catalogs(Path(catalog_dir), catalog_lang)
        self._lock = threading.Lock()

    def info(self) -> dict:
        return {
            "detector": self.detector_weights.name,
            "roi": self.roi_weights.name,
            "obb_imgsz": self.obb_imgsz,
            "device": str(self.device),
            "card_conf": self.card_conf,
            "roi_conf": self.roi_conf,
            "catalog_cards": int(len(self.catalog)),
            "catalog_sets": int(self.catalog["set_id"].nunique()),
            "catalog_langs": sorted(self.catalog["lang"].unique().tolist()),
            "ocr_langs": getattr(self.reader, "langs", []),
        }

    def scan_bytes(
        self,
        data: bytes,
        filename: str,
        *,
        include_crops: bool = False,
        set_id: str = "",
        top_n: int | None = None,
    ) -> dict:
        try:
            bgr = decode_image(data)
        except ValueError as err:
            return {
                "filename": filename,
                "width": 0,
                "height": 0,
                "card_count": 0,
                "cards": [],
                "error": str(err),
            }
        return self.scan_bgr(
            bgr,
            filename,
            include_crops=include_crops,
            set_id=set_id,
            top_n=top_n,
        )

    def scan_bgr(
        self,
        bgr: np.ndarray,
        filename: str,
        *,
        include_crops: bool = False,
        set_id: str = "",
        top_n: int | None = None,
    ) -> dict:
        height, width = int(bgr.shape[0]), int(bgr.shape[1])
        n = top_n if top_n is not None else self.top_n
        with self._lock:
            pred = self.card_model.predict(
                source=bgr,
                conf=self.card_conf,
                imgsz=self.obb_imgsz,
                device=self.device,
                verbose=False,
            )[0]
            crops = sort_crops(crop_result(pred, enhance=True, frame=False), pred.orig_img.shape)
            cards = []
            for order, card in enumerate(crops):
                orig_bgr = card_to_bgr(card)
                orient_bgr, roi, orient_deg = orient_printed_up(
                    self.roi_model, orig_bgr, self.roi_conf, self.device
                )
                read = read_card(roi, self.reader, image=orient_bgr, conf_min=self.roi_conf)
                ranked = (
                    match_catalog(
                        read.name,
                        read.number,
                        read.collection,
                        self.catalog,
                        set_id=set_id,
                        top_n=n,
                    )
                    if has_collector_number(read.number)
                    else None
                )
                matches = []
                if ranked is not None:
                    for _, row in ranked.iterrows():
                        matches.append(
                            {
                                "name": str(row["name"]),
                                "number": str(row["number"]),
                                "set_id": str(row["set_id"]),
                                "set_name": str(row["set_name"]),
                                "rarity": str(row.get("rarity") or ""),
                                "lang": str(row.get("lang") or ""),
                                "score": round(float(row["score"]), 3),
                            }
                        )
                best = matches[0] if matches else None
                crop_h, crop_w = orient_bgr.shape[:2]
                payload = {
                    "index": order,
                    "det_conf": round(float(card.conf), 3),
                    "orient_deg": int(orient_deg),
                    "quad": quad_to_list(card.quad),
                    "ocr": {
                        "name": read.name,
                        "number": read.number,
                        "collection": read.collection,
                    },
                    "roi": {
                        field: {
                            "source": region.source,
                            "conf": round(float(region.conf), 3),
                            "ocr_conf": round(float(region.ocr_conf), 3),
                            "text": region.text or getattr(read, field, ""),
                            "raw": region.raw or "",
                            "quad": quad_norm(region.quad, crop_w, crop_h),
                        }
                        for field, region in read.regions.items()
                    },
                    "match": best,
                    "matches": matches,
                }
                if include_crops:
                    payload["crop_jpeg_base64"] = bgr_to_jpeg_b64(
                        orient_bgr, quality=self.jpeg_quality
                    )
                cards.append(payload)
        return {
            "filename": filename,
            "width": width,
            "height": height,
            "card_count": len(cards),
            "cards": cards,
            "error": None,
        }

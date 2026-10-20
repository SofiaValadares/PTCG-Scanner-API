from __future__ import annotations

import cv2
import numpy as np

_ROI_NAME_KEYS = {"name"}
_ROI_NUMBER_KEYS = {"number"}
_ROI_COLLECTION_KEYS = {"collection", "colection"}


def _roi_class_ids(pred, keys: set[str]) -> set[int]:
    names = getattr(pred, "names", None) or {}
    ids = set()
    for cid, label in names.items():
        if str(label).lower() in keys:
            ids.add(int(cid))
    return ids


def _roi_band(pred, keys: set[str], width: float, height: float, *, wide: bool = False) -> dict | None:
    boxes = getattr(pred, "obb", None) or getattr(pred, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return None
    target = _roi_class_ids(pred, keys)
    if not target:
        return None
    cls = boxes.cls.detach().cpu().numpy()
    conf = boxes.conf.detach().cpu().numpy()
    if hasattr(boxes, "xyxyxyxy") and boxes.xyxyxyxy is not None:
        pts = boxes.xyxyxyxy.detach().cpu().numpy().reshape(len(boxes), -1, 2)
        cx = pts[:, :, 0].mean(axis=1)
        cy = pts[:, :, 1].mean(axis=1)
        bw = pts[:, :, 0].max(axis=1) - pts[:, :, 0].min(axis=1)
        bh = pts[:, :, 1].max(axis=1) - pts[:, :, 1].min(axis=1)
    else:
        xyxy = boxes.xyxy.detach().cpu().numpy()
        cx = (xyxy[:, 0] + xyxy[:, 2]) / 2.0
        cy = (xyxy[:, 1] + xyxy[:, 3]) / 2.0
        bw = xyxy[:, 2] - xyxy[:, 0]
        bh = xyxy[:, 3] - xyxy[:, 1]
    best = None
    best_conf = -1.0
    fallback = None
    fallback_conf = -1.0
    for i, cid in enumerate(cls):
        if int(cid) not in target:
            continue
        box = {
            "cy": float(cy[i]),
            "cx": float(cx[i]),
            "bw": float(bw[i]),
            "bh": float(bh[i]),
            "conf": float(conf[i]),
        }
        if box["conf"] > fallback_conf:
            fallback_conf = box["conf"]
            fallback = box
        if wide and (box["bw"] < 0.32 * width or box["bh"] > 0.28 * height):
            continue
        if box["conf"] > best_conf:
            best_conf = box["conf"]
            best = box
    return best if best is not None else fallback


def upright_layout_score(pred, height: int, width: int) -> tuple[float, bool]:
    h = max(float(height), 1.0)
    w = max(float(width), 1.0)
    name = _roi_band(pred, _ROI_NAME_KEYS, w, h, wide=True)
    number = _roi_band(pred, _ROI_NUMBER_KEYS, w, h, wide=False)
    collection = _roi_band(pred, _ROI_COLLECTION_KEYS, w, h, wide=False)
    score = 0.0
    if name is not None and number is not None:
        rel = (number["cy"] - name["cy"]) / h
        score += rel * min(name["conf"], number["conf"])
        score += 0.28 * min(name["conf"], number["conf"])
    elif name is not None:
        score += (0.5 - name["cy"] / h) * name["conf"]
    elif number is not None:
        score += (number["cy"] / h - 0.5) * number["conf"]
    if name is not None:
        yn = name["cy"] / h
        if yn > 0.5:
            score -= 0.4 * name["conf"]
        else:
            score += 0.18 * name["conf"] * max(0.0, 0.32 - yn) / 0.32
    if number is not None:
        ynum = number["cy"] / h
        if ynum < 0.5:
            score -= 0.28 * number["conf"]
        else:
            score += 0.14 * number["conf"]
    if collection is not None:
        yc = collection["cy"] / h
        score += (0.14 if yc > 0.55 else -0.14) * collection["conf"]
    return score, name is not None and number is not None


def predict_roi(model, bgr: np.ndarray, conf: float, device: str | int):
    return model.predict(
        source=bgr,
        conf=conf,
        imgsz=800,
        device=device,
        verbose=False,
    )[0]


def orient_printed_up(model, crop_bgr: np.ndarray, conf: float, device: str | int):
    flipped_bgr = cv2.rotate(crop_bgr, cv2.ROTATE_180)
    roi0 = predict_roi(model, crop_bgr, conf, device)
    roi180 = predict_roi(model, flipped_bgr, conf, device)
    h, w = crop_bgr.shape[:2]
    s0, both0 = upright_layout_score(roi0, h, w)
    s180, both180 = upright_layout_score(roi180, h, w)
    if both180 and not both0:
        return flipped_bgr, roi180, 180
    if both0 and not both180:
        return crop_bgr, roi0, 0
    if s180 > s0 + 0.02:
        return flipped_bgr, roi180, 180
    return crop_bgr, roi0, 0

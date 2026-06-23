"""Automatic Number Plate Recognition (ANPR).

Pipeline per the deck: plate localization -> binarization (contrast adjustment) ->
character OCR via Tesseract -> logging of the parsed alphanumeric string.

Plate localization uses an optional dedicated YOLO plate model when configured;
otherwise it falls back to a classic contour/edge heuristic on the vehicle crop.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PlateResult:
    text: str
    confidence: float


class ANPR:
    def __init__(self, cfg) -> None:
        a = cfg.get("anpr", {}) or {}
        self.enabled = bool(a.get("enabled", True))
        self.min_conf = float(a.get("min_confidence", 0.4))
        self.regex = re.compile(a.get("plate_regex", "^[A-Z0-9]{4,12}$"))
        self._plate_model = None
        self._tesseract_ok = False

        if not self.enabled:
            return

        tess_cmd = a.get("tesseract_cmd", "")
        try:
            import pytesseract

            if tess_cmd:
                pytesseract.pytesseract.tesseract_cmd = tess_cmd
            self._pytesseract = pytesseract
            self._tesseract_ok = True
        except Exception:  # pragma: no cover - environment dependent
            self._tesseract_ok = False

        model_path = a.get("plate_model", "")
        if model_path:
            try:
                from ultralytics import YOLO

                self._plate_model = YOLO(model_path)
            except Exception:  # pragma: no cover
                self._plate_model = None

    # ---- localization -----------------------------------------------------
    def _localize(self, vehicle_crop):
        """Return the plate region (sub-image) or None."""
        import cv2

        if self._plate_model is not None:
            res = self._plate_model(vehicle_crop, verbose=False)
            if res and res[0].boxes is not None and len(res[0].boxes) > 0:
                # pick the highest-confidence plate box
                boxes = res[0].boxes
                idx = int(boxes.conf.argmax())
                x1, y1, x2, y2 = (int(v) for v in boxes.xyxy[idx].tolist())
                return vehicle_crop[y1:y2, x1:x2]
            return None

        # Heuristic fallback: find a bright, wide-ish rectangular contour.
        gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        edged = cv2.Canny(gray, 30, 200)
        contours, _ = cv2.findContours(
            edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.018 * peri, True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                if w > h and w >= 60 and 1.8 <= (w / float(h or 1)) <= 6.0:
                    return vehicle_crop[y : y + h, x : x + w]
        return None

    # ---- ocr --------------------------------------------------------------
    def _ocr(self, plate_img) -> Optional[PlateResult]:
        import cv2

        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        # Binarization (contrast adjustment for text).
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        data = self._pytesseract.image_to_data(
            binary, config=config, output_type=self._pytesseract.Output.DICT
        )

        best_text, best_conf = "", -1.0
        for token, conf in zip(data["text"], data["conf"]):
            token = re.sub(r"[^A-Z0-9]", "", token.upper())
            try:
                conf_val = float(conf)
            except (TypeError, ValueError):
                conf_val = -1.0
            if token and conf_val > best_conf:
                best_text, best_conf = token, conf_val

        if not best_text:
            return None
        confidence = max(best_conf, 0.0) / 100.0
        return PlateResult(text=best_text, confidence=confidence)

    # ---- public -----------------------------------------------------------
    def read(self, vehicle_crop) -> Optional[PlateResult]:
        """Read a plate from a vehicle crop. Returns a validated PlateResult or None."""
        if not self.enabled or not self._tesseract_ok:
            return None
        if vehicle_crop is None or vehicle_crop.size == 0:
            return None

        plate_img = self._localize(vehicle_crop)
        if plate_img is None or plate_img.size == 0:
            return None

        result = self._ocr(plate_img)
        if result is None:
            return None
        if result.confidence < self.min_conf:
            return None
        if not self.regex.match(result.text):
            return None
        return result

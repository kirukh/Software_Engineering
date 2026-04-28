"""YoloDetector — DetectorProtocol-Implementierung mit YOLOv8 + Webcam."""
from __future__ import annotations

import os
import time

import cv2
from ultralytics import YOLO

from vision_interface import VisionResult

STABLE_FRAMES_REQUIRED = int(os.environ.get("VISION_STABLE_FRAMES", "8"))
CONFIDENCE_MIN = float(os.environ.get("VISION_CONFIDENCE_MIN", "0.5"))
CAMERA_INDEX = int(os.environ.get("VISION_CAMERA_INDEX", "0"))
MODEL_PATH = os.environ.get("VISION_MODEL_PATH", "yolov8n.pt")
TIMEOUT_SECONDS = float(os.environ.get("VISION_TIMEOUT", "30"))

# Mapping: User-Begriff (DE/EN, Umgangssprache) → COCO-Label(s) von YOLOv8.
_LABEL_ALIASES: dict[str, frozenset[str]] = {
    "smartphone": frozenset({"cell phone"}),
    "handy":      frozenset({"cell phone"}),
    "phone":      frozenset({"cell phone"}),
    "cell phone": frozenset({"cell phone"}),
    "laptop":     frozenset({"laptop"}),
    "person":     frozenset({"person"}),
    "bottle":     frozenset({"bottle"}),
    "cup":        frozenset({"cup"}),
    "chair":      frozenset({"chair"}),
    "book":       frozenset({"book"}),
    "keyboard":   frozenset({"keyboard"}),
    "mouse":      frozenset({"mouse"}),
    "tv":         frozenset({"tv"}),
    "backpack":   frozenset({"backpack"}),
}


def _resolve_labels(object_name: str) -> frozenset[str]:
    return _LABEL_ALIASES.get(object_name.lower(), frozenset({object_name.lower()}))


class YoloDetector:
    def __init__(self) -> None:
        self._model: YOLO | None = None

    def _model_lazy(self) -> YOLO:
        # Lazy-Load: Modell erst beim ersten detect() laden, nicht beim Import.
        if self._model is None:
            self._model = YOLO(MODEL_PATH)
        return self._model

    def detect(self, object_name: str) -> VisionResult:
        model = self._model_lazy()
        target_labels = _resolve_labels(object_name)
        names: dict[int, str] = model.names

        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            raise RuntimeError(f"Kamera {CAMERA_INDEX} konnte nicht geöffnet werden.")

        stable_count = 0
        last = (0.0, 0.0, 0.0)  # (conf, x, y)
        deadline = time.monotonic() + TIMEOUT_SECONDS

        try:
            while time.monotonic() < deadline:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue

                results = model.predict(frame, conf=CONFIDENCE_MIN, verbose=False, imgsz=640)
                match = _best_match(results[0], names, target_labels)

                if match is None:
                    stable_count = 0
                    continue

                # Treffer muss N Frames in Folge stabil sein → reduziert False Positives.
                last = match
                stable_count += 1
                if stable_count >= STABLE_FRAMES_REQUIRED:
                    conf, x, y = last
                    return VisionResult(object_name, True, round(conf, 4), round(x, 4), round(y, 4))
        finally:
            cap.release()

        return VisionResult(object_name, False, 0.0)


def _best_match(result, names, target_labels) -> tuple[float, float, float] | None:
    """Liefert (conf, x_norm, y_norm) der besten passenden Box, oder None."""
    if result.boxes is None or len(result.boxes) == 0:
        return None

    img_h, img_w = result.orig_shape
    targets_lower = {lbl.lower() for lbl in target_labels}
    best = None

    for box in result.boxes:
        label = names.get(int(box.cls[0]), "").lower()
        if label not in targets_lower:
            continue
        conf = float(box.conf[0])
        if best is None or conf > best[0]:
            x_px, y_px, _, _ = box.xywh[0].tolist()
            best = (conf, x_px / img_w, y_px / img_h)

    return best
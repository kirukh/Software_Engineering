"""
YoloDetector — DetectorProtocol-Implementierung mit YOLOv8 + Webcam.
"""
from __future__ import annotations

import os
import time

import cv2
from ultralytics import YOLO

from vision_interface import DetectorProtocol, VisionResult

STABLE_FRAMES_REQUIRED = int(os.environ.get("VISION_STABLE_FRAMES", "8"))
CONFIDENCE_MIN = float(os.environ.get("VISION_CONFIDENCE_MIN", "0.5"))
CAMERA_INDEX = int(os.environ.get("VISION_CAMERA_INDEX", "0"))
MODEL_PATH = os.environ.get("VISION_MODEL_PATH", "yolov8n.pt")
TIMEOUT_SECONDS = float(os.environ.get("VISION_TIMEOUT", "30"))

_LABEL_ALIASES: dict[str, frozenset[str]] = {
    "smartphone":   frozenset({"cell phone"}),
    "handy":        frozenset({"cell phone"}),
    "phone":        frozenset({"cell phone"}),
    "cell phone":   frozenset({"cell phone"}),
    "laptop":       frozenset({"laptop"}),
    "person":       frozenset({"person"}),
    "bottle":       frozenset({"bottle"}),
    "cup":          frozenset({"cup"}),
    "chair":        frozenset({"chair"}),
    "book":         frozenset({"book"}),
    "keyboard":     frozenset({"keyboard"}),
    "mouse":        frozenset({"mouse"}),
    "tv":           frozenset({"tv"}),
    "backpack":     frozenset({"backpack"}),
}


def _resolve_labels(object_name: str) -> frozenset[str]:
    key = object_name.strip().lower()
    return _LABEL_ALIASES.get(key, frozenset({key}))


class YoloDetector:
    def __init__(self) -> None:
        self._model: YOLO | None = None

    def _get_model(self) -> YOLO:
        if self._model is None:
            print(f"[YoloDetector] Lade Modell: {MODEL_PATH}")
            self._model = YOLO(MODEL_PATH)
        return self._model

    def detect(self, object_name: str) -> VisionResult:
        model = self._get_model()
        target_labels = _resolve_labels(object_name)
        names: dict[int, str] = model.names

        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            raise RuntimeError(
                f"Kamera {CAMERA_INDEX} konnte nicht geöffnet werden."
            )

        print(
            f"[YoloDetector] Suche nach '{object_name}' "
            f"(COCO-Labels: {target_labels}) | "
            f"conf≥{CONFIDENCE_MIN} | stable={STABLE_FRAMES_REQUIRED} | "
            f"timeout={TIMEOUT_SECONDS}s"
        )

        stable_count = 0
        last_conf = 0.0
        last_x = None
        last_y = None
        deadline = time.monotonic() + TIMEOUT_SECONDS

        try:
            while time.monotonic() < deadline:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue

                results = model.predict(
                    source=frame,
                    conf=CONFIDENCE_MIN,
                    verbose=False,
                    imgsz=640,
                )

                match = _best_match(results[0], names, target_labels)

                if match is not None:
                    best_conf, best_x, best_y = match
                    stable_count += 1
                    last_conf, last_x, last_y = best_conf, best_x, best_y
                    print(
                        f"[YoloDetector] Erkannt: conf={best_conf:.2f} "
                        f"stable={stable_count}/{STABLE_FRAMES_REQUIRED}"
                    )
                    if stable_count >= STABLE_FRAMES_REQUIRED:
                        print(f"[YoloDetector] Stabil erkannt → found=True")
                        return VisionResult(
                            name=object_name,
                            found=True,
                            confidence=round(last_conf, 4),
                            x=round(last_x, 4),
                            y=round(last_y, 4),
                        )
                else:
                    if stable_count > 0:
                        print(f"[YoloDetector] Verloren — stable_count reset")
                    stable_count = 0

        finally:
            cap.release()

        print(f"[YoloDetector] Timeout nach {TIMEOUT_SECONDS}s — nicht gefunden")
        return VisionResult(name=object_name, found=False, confidence=0.0)


def _best_match(
    result,
    names: dict[int, str],
    target_labels: frozenset[str],
) -> tuple[float, float, float] | None:
    if result.boxes is None or len(result.boxes) == 0:
        return None

    best_conf = 0.0
    best_x = 0.0
    best_y = 0.0
    img_h, img_w = result.orig_shape

    for box in result.boxes:
        label = names.get(int(box.cls[0]), "").lower()
        conf = float(box.conf[0])
        if label in {lbl.lower() for lbl in target_labels}:
            if conf > best_conf:
                best_conf = conf
                x_px, y_px, _, _ = box.xywh[0].tolist()
                best_x = x_px / img_w
                best_y = y_px / img_h

    if best_conf == 0.0:
        return None

    return (best_conf, best_x, best_y)


assert isinstance(YoloDetector(), DetectorProtocol), (
    "YoloDetector implementiert DetectorProtocol nicht korrekt"
)
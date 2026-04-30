"""YoloDetector — DetectorProtocol-Implementierung mit YOLOv8 + Webcam."""
from __future__ import annotations

import os
import threading
import time

import cv2
from ultralytics import YOLO

from vision_interface import FrameCallback, VisionResult

CONFIDENCE_MIN = float(os.environ.get("VISION_CONFIDENCE_MIN", "0.5"))
CAMERA_INDEX = int(os.environ.get("VISION_CAMERA_INDEX", "0"))
MODEL_PATH = os.environ.get("VISION_MODEL_PATH", "yolov8n.pt")

# Hinweis: Der Controller liefert immer bereits korrekte COCO-Labels
# (Mapping passiert im Audio-Team). Daher kein Aliasing hier nötig.


class YoloDetector:
    def __init__(self) -> None:
        self._model: YOLO | None = None

    def _model_lazy(self) -> YOLO:
        if self._model is None:
            self._model = YOLO(MODEL_PATH)
        return self._model

    def prewarm(self) -> None:
        """Modell vorladen — vom Server beim Start aufgerufen."""
        self._model_lazy()

    def stream(
        self,
        object_name: str,
        on_frame: FrameCallback,
        stop_event: threading.Event,
    ) -> None:
        model = self._model_lazy()
        target = object_name.lower()
        names: dict[int, str] = model.names

        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            raise RuntimeError(f"Kamera {CAMERA_INDEX} konnte nicht geöffnet werden.")

        try:
            while not stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue

                results = model.predict(frame, conf=CONFIDENCE_MIN, verbose=False, imgsz=640)
                match = _best_match(results[0], names, target)

                if match is None:
                    on_frame(VisionResult(object_name, False, 0.0))
                else:
                    conf, x, y, w, h = match
                    on_frame(VisionResult(
                        object_name, True,
                        round(conf, 4),
                        round(x, 4), round(y, 4),
                        round(w, 4), round(h, 4),
                    ))
        finally:
            cap.release()


def _best_match(result, names: dict, target: str):
    """Beste passende Box als (conf, x, y, w, h) normiert auf 0..1, oder None."""
    if result.boxes is None or len(result.boxes) == 0:
        return None

    img_h, img_w = result.orig_shape
    best = None

    for box in result.boxes:
        label = names.get(int(box.cls[0]), "").lower()
        if label != target:
            continue
        conf = float(box.conf[0])
        if best is None or conf > best[0]:
            x_px, y_px, w_px, h_px = box.xywh[0].tolist()
            best = (conf, x_px / img_w, y_px / img_h, w_px / img_w, h_px / img_h)

    return best
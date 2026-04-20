"""
YoloDetector — DetectorProtocol-Implementierung mit YOLOv8 + Webcam.

Kein Hailo nötig — läuft auf jedem Laptop/PC mit Kamera.
Gleiche stabile-Frames-Logik wie HailoDetector.

Umgebungsvariablen:
    VISION_STABLE_FRAMES   Anzahl konsekutiver Frames für stabile Erkennung (default: 8)
    VISION_CONFIDENCE_MIN  Mindest-Konfidenz 0.0–1.0 (default: 0.5)
    VISION_CAMERA_INDEX    Webcam-Index (default: 0)
    VISION_MODEL_PATH      Pfad zum YOLO-Modell (default: yolov8n.pt)
    VISION_TIMEOUT         Maximale Suchzeit in Sekunden (default: 30)
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

# Mapping: normalisierter Suchbegriff → COCO-Label(s) die YOLO kennt
# Damit kann der Controller z.B. "smartphone" übergeben, auch wenn YOLO "cell phone" sagt.
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
    """Gibt die YOLO-COCO-Labels zurück die zu object_name passen."""
    key = object_name.strip().lower()
    return _LABEL_ALIASES.get(key, frozenset({key}))


class YoloDetector:
    """
    Detektor auf Basis von YOLOv8 + OpenCV Webcam.

    Implementiert DetectorProtocol — austauschbar mit HailoDetector und MockDetector.

    Öffnet die Kamera, liest Frames und sucht nach object_name bis
    STABLE_FRAMES_REQUIRED konsekutive Frames über CONFIDENCE_MIN gefunden wurden
    oder TIMEOUT_SECONDS abgelaufen sind.

    Beispiel:
        detector = YoloDetector()
        result = detector.detect("smartphone")
        print(result.to_dict())
        # → {"name": "smartphone", "found": True, "confidence": 0.87}
    """

    def __init__(self) -> None:
        self._model: YOLO | None = None

    def _get_model(self) -> YOLO:
        """Lädt das YOLO-Modell lazy (nur einmal)."""
        if self._model is None:
            print(f"[YoloDetector] Lade Modell: {MODEL_PATH}")
            self._model = YOLO(MODEL_PATH)
        return self._model

    def detect(self, object_name: str) -> VisionResult:
        """
        Öffnet Webcam und sucht nach object_name.

        Blockiert bis Objekt stabil erkannt oder Timeout erreicht.

        Args:
            object_name: Gesuchtes Objekt, z.B. "smartphone"

        Returns:
            VisionResult mit found=True/False und letzter Konfidenz
        """
        model = self._get_model()
        target_labels = _resolve_labels(object_name)
        names: dict[int, str] = model.names

        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            raise RuntimeError(
                f"Kamera {CAMERA_INDEX} konnte nicht geöffnet werden. "
                f"VISION_CAMERA_INDEX prüfen."
            )

        print(
            f"[YoloDetector] Suche nach '{object_name}' "
            f"(COCO-Labels: {target_labels}) | "
            f"conf≥{CONFIDENCE_MIN} | stable={STABLE_FRAMES_REQUIRED} | "
            f"timeout={TIMEOUT_SECONDS}s"
        )

        stable_count = 0
        last_conf = 0.0
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

                best_conf = _best_match_confidence(results[0], names, target_labels)

                if best_conf is not None:
                    stable_count += 1
                    last_conf = best_conf
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
                        )
                else:
                    if stable_count > 0:
                        print(f"[YoloDetector] Verloren — stable_count reset")
                    stable_count = 0

        finally:
            cap.release()

        print(f"[YoloDetector] Timeout nach {TIMEOUT_SECONDS}s — nicht gefunden")
        return VisionResult(name=object_name, found=False, confidence=0.0)


def _best_match_confidence(
    result,
    names: dict[int, str],
    target_labels: frozenset[str],
) -> float | None:
    """
    Gibt die höchste Konfidenz eines passenden Objekts zurück, oder None.
    """
    if result.boxes is None or len(result.boxes) == 0:
        return None

    best = None
    for box in result.boxes:
        label = names.get(int(box.cls[0]), "").lower()
        conf = float(box.conf[0])
        if label in {lbl.lower() for lbl in target_labels}:
            if best is None or conf > best:
                best = conf
    return best


# Protokoll-Check
assert isinstance(YoloDetector(), DetectorProtocol), (
    "YoloDetector implementiert DetectorProtocol nicht korrekt"
)

"""
visual.py — Zentrale Implementierung des Visual-Teams (Sprint 1).

Öffentliche API:
    search(object_name: str) -> dict

Rückgabe-Dict:
    {"name": str, "found": bool, "confidence": float}

Detektor-Auswahl (automatisch oder per Umgebungsvariable):
    VISUAL_DETECTOR=hailo   → HailoDetector  (Raspberry Pi + Hailo-8)
    VISUAL_DETECTOR=yolo    → YoloDetector   (Webcam + YOLOv8, default)
    VISUAL_DETECTOR=mock    → MockDetector   (kein Hardware, für Tests)

    Ohne Variable: Hailo → YOLO → Mock (erste verfügbare Option)

Verwendung durch Controller:
    from visual import search
    result = search("smartphone")
    # → {"name": "smartphone", "found": True, "confidence": 0.91}
"""
from __future__ import annotations

import os

from vision_interface import DetectorProtocol, VisionResult


# ---------------------------------------------------------------------------
# Modul-Level Singleton (lazy initialisiert)
# ---------------------------------------------------------------------------

_detector: DetectorProtocol | None = None


def _get_detector() -> DetectorProtocol:
    """
    Gibt den aktiven Detektor zurück.

    Auswahl-Logik:
      VISUAL_DETECTOR=mock   → MockDetector  (Tests / kein Hardware)
      VISUAL_DETECTOR=yolo   → YoloDetector  (Webcam + YOLOv8)
      VISUAL_DETECTOR=hailo  → HailoDetector (Raspberry Pi + Hailo-8)
      Nicht gesetzt          → Hailo (wenn verfügbar) → YOLO → Mock
    """
    global _detector
    if _detector is not None:
        return _detector

    mode = os.environ.get("VISUAL_DETECTOR", "").strip().lower()

    # Explizite Auswahl per Umgebungsvariable
    if mode == "yolo":
        from yolo_detector import YoloDetector
        _detector = YoloDetector()
        print("[visual] YoloDetector aktiv (VISUAL_DETECTOR=yolo)")
        return _detector

    if mode == "hailo":
        from hailo_detector import HailoDetector, _hailo_available
        if not _hailo_available:
            raise RuntimeError("VISUAL_DETECTOR=hailo gesetzt, aber Hailo nicht verfügbar.")
        _detector = HailoDetector()
        print("[visual] HailoDetector aktiv (VISUAL_DETECTOR=hailo)")
        return _detector

    # Auto-Fallback: Hailo → YOLO → Mock
    try:
        from hailo_detector import HailoDetector, _hailo_available
        if not _hailo_available:
            raise ImportError
        _detector = HailoDetector()
        print("[visual] HailoDetector aktiv (auto)")
    except ImportError:
            from yolo_detector import YoloDetector
            _detector = YoloDetector()
            print("[visual] YoloDetector aktiv (auto-fallback: kein Hailo)")      
    return _detector


def set_detector(detector: DetectorProtocol) -> None:
    """
    Setzt einen benutzerdefinierten Detektor (z.B. für Tests oder Dependency Injection).

    Beispiel:
        from mock_detector import MockDetector
        from visual import set_detector
        set_detector(MockDetector(found_objects={"cup"}))
    """
    global _detector
    _detector = detector


# ---------------------------------------------------------------------------
# Zentrale search()-Funktion (T-05, US-03)
# ---------------------------------------------------------------------------

def search(object_name: str) -> dict:
    """
    Sucht nach object_name im Kamerastream.

    Schnittstelle zum Controller (ITF-01, ITF-02):
        Eingabe:  object_name (str) — z.B. "smartphone"
        Ausgabe:  dict mit den Feldern name, found, confidence

    Rückgabe-Beispiele:
        {"name": "smartphone", "found": True,  "confidence": 0.91}
        {"name": "smartphone", "found": False, "confidence": 0.0}

    Args:
        object_name: Name des gesuchten Objekts (wie vom Audio-Team übergeben)

    Returns:
        dict: {"name": str, "found": bool, "confidence": float}
    """
    if not object_name or not isinstance(object_name, str):
        raise ValueError(f"object_name muss ein nicht-leerer String sein, bekam: {object_name!r}")

    detector = _get_detector()
    result: VisionResult = detector.detect(object_name.strip())
    return result.to_dict()

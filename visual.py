"""
visual.py — Zentrale Implementierung des Visual-Teams (Sprint 1).

Öffentliche API:
    search(object_name: str) -> dict

Rückgabe-Dict:
    {"name": str, "found": bool, "confidence": float, "x": float|None, "y": float|None}
"""
from __future__ import annotations

import os

from vision_interface import DetectorProtocol, VisionResult

_detector: DetectorProtocol | None = None


def _get_detector() -> DetectorProtocol:
    global _detector
    if _detector is not None:
        return _detector

    mode = os.environ.get("VISUAL_DETECTOR", "").strip().lower()

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
    global _detector
    _detector = detector


def search(object_name: str) -> dict:
    if not object_name or not isinstance(object_name, str):
        raise ValueError(f"object_name muss ein nicht-leerer String sein, bekam: {object_name!r}")

    detector = _get_detector()
    result: VisionResult = detector.detect(object_name.strip())
    return result.to_dict()
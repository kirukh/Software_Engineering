"""
visual.py — Tracking-API des Visual-Moduls.

Logik-Schicht zwischen HTTP (server.py) und Detector:
    start_tracking(name)   # Detector im Hintergrund starten
    get_latest()           # aktuelles aggregiertes Window-Ergebnis
    stop_tracking()        # Detector sauber beenden
    prewarm()              # Modell vorladen (vom Server beim Start)

Aggregation: Sliding Window über die letzten N Roh-Frames vom Detector
(Default 8). Mind. M Treffer (Default 5) im Fenster → found=True mit
Mittelwerten. Sonst found=False.

Detector-Wahl per VISUAL_DETECTOR=hailo|yolo (sonst Auto: Hailo > YOLO).
"""
from __future__ import annotations

import os
import threading
from collections import deque

from vision_interface import DetectorProtocol, VisionResult

# ------------------------------------------------------------------ Config

WINDOW_SIZE = int(os.environ.get("VISION_WINDOW_SIZE", "8"))
MIN_HITS_IN_WINDOW = int(os.environ.get("VISION_MIN_HITS_IN_WINDOW", "5"))


# ------------------------------------------------------------------ State

_detector: DetectorProtocol | None = None

_tracking_lock = threading.Lock()
_tracking_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None
_current_name: str | None = None

_window_lock = threading.Lock()
_window: deque[VisionResult] = deque(maxlen=WINDOW_SIZE)


# ------------------------------------------------------------------ Detector-Wahl

def _get_detector() -> DetectorProtocol:
    global _detector
    if _detector is not None:
        return _detector

    mode = os.environ.get("VISUAL_DETECTOR", "").strip().lower()

    if mode == "yolo":
        from yolo_detector import YoloDetector
        _detector = YoloDetector()
    elif mode == "hailo":
        from hailo_detector import HailoDetector, _hailo_available
        if not _hailo_available:
            raise RuntimeError("VISUAL_DETECTOR=hailo gesetzt, aber Hailo nicht verfügbar.")
        _detector = HailoDetector()
    else:
        # Auto: Hailo bevorzugt, YOLO als Fallback ohne Hardware
        try:
            from hailo_detector import HailoDetector, _hailo_available
            if not _hailo_available:
                raise ImportError
            _detector = HailoDetector()
        except ImportError:
            from yolo_detector import YoloDetector
            _detector = YoloDetector()

    print(f"[visual] {type(_detector).__name__} aktiv")
    return _detector


def set_detector(detector: DetectorProtocol | None) -> None:
    """Erlaubt Tests, einen eigenen Detector zu injizieren (oder zurückzusetzen)."""
    global _detector
    _detector = detector


def prewarm() -> None:
    """Detector initialisieren und Modell vorladen. Vom Server beim Start aufgerufen."""
    detector = _get_detector()
    if hasattr(detector, "prewarm"):
        detector.prewarm()


# ------------------------------------------------------------------ Aggregation

def _on_frame(frame: VisionResult) -> None:
    with _window_lock:
        _window.append(frame)


def _aggregate() -> dict:
    """Window → Dict. Mittelwerte über Treffer-Frames, sonst found=False."""
    with _window_lock:
        snapshot = list(_window)
        name = _current_name or ""

    hits = [f for f in snapshot if f.found]
    if len(hits) < MIN_HITS_IN_WINDOW:
        return _empty_result(name)

    n = len(hits)
    return {
        "name": name,
        "found": True,
        "confidence": round(sum(f.confidence for f in hits) / n, 4),
        "x": round(sum(f.x for f in hits) / n, 4),
        "y": round(sum(f.y for f in hits) / n, 4),
        "w": round(sum(f.w for f in hits) / n, 4),
        "h": round(sum(f.h for f in hits) / n, 4),
    }


def _empty_result(name: str) -> dict:
    return {
        "name": name,
        "found": False,
        "confidence": 0.0,
        "x": None, "y": None, "w": None, "h": None,
    }


# ------------------------------------------------------------------ Tracking-API

def start_tracking(name: str) -> dict:
    """Startet den Detector im Hintergrund. Idempotent: laufendes Tracking
    wird vorher gestoppt, falls der Name sich ändert.

    Validation passiert im Server (Pydantic). Hier nur defensives strip().
    """
    global _tracking_thread, _stop_event, _current_name
    name = name.strip()

    with _tracking_lock:
        if _tracking_thread is not None and _tracking_thread.is_alive():
            if _current_name == name:
                return {"status": "running", "name": name}
            _stop_locked()

        with _window_lock:
            _window.clear()

        _current_name = name
        _stop_event = threading.Event()
        detector = _get_detector()
        _tracking_thread = threading.Thread(
            target=_run_stream,
            args=(detector, name, _stop_event),
            daemon=True,
        )
        _tracking_thread.start()

    return {"status": "running", "name": name}


def _run_stream(detector: DetectorProtocol, name: str, stop_event: threading.Event) -> None:
    """Worker: ruft detector.stream() bis stop_event gesetzt wird."""
    try:
        detector.stream(name, _on_frame, stop_event)
    except Exception as e:
        print(f"[visual] Stream-Fehler: {e}")
        with _window_lock:
            _window.clear()


def get_latest() -> dict:
    """Aktuelles aggregiertes Window-Ergebnis. status='idle' wenn nichts läuft."""
    with _tracking_lock:
        running = _tracking_thread is not None and _tracking_thread.is_alive()

    if not running:
        return {"status": "idle"}

    return {"status": "running", **_aggregate()}


def stop_tracking() -> dict:
    """Stoppt den laufenden Detector. Idempotent."""
    with _tracking_lock:
        was_running = _tracking_thread is not None and _tracking_thread.is_alive()
        _stop_locked()
    return {"status": "stopped", "was_running": was_running}


def _stop_locked() -> None:
    """Muss unter _tracking_lock aufgerufen werden."""
    global _tracking_thread, _stop_event, _current_name
    if _stop_event is not None:
        _stop_event.set()
    if _tracking_thread is not None:
        _tracking_thread.join(timeout=2.0)
    _tracking_thread = None
    _stop_event = None
    _current_name = None
    with _window_lock:
        _window.clear()
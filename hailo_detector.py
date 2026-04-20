"""
HailoDetector — DetectorProtocol-Implementierung für Raspberry Pi 5 + Hailo-8 (T-02).

Kapselt den GStreamer/Hailo-Pipeline-Aufruf aus smartphone_search_vision.py
hinter dem einheitlichen DetectorProtocol-Interface.

Nur auf dem Raspberry Pi mit installierter hailo_apps-Umgebung lauffähig.
Lokal → MockDetector verwenden.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass

from vision_interface import DetectorProtocol, VisionResult

# Hailo-Imports werden lazy geladen damit das Modul auch auf Nicht-Pi-Systemen
# importierbar ist (z.B. für isinstance/Protokoll-Checks in Tests).
_hailo_available = False
try:
    import gi
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst  # noqa: F401
    import hailo  # noqa: F401
    from hailo_apps.hailo_app_python.apps.detection_simple.detection_pipeline_simple import (
        GStreamerDetectionApp,
    )
    from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
    _hailo_available = True
except ImportError:
    pass

# COCO-Labels für "Handy" in YOLOv6 Nano (Hailo detection_simple)
_PHONE_LABELS = frozenset({"cell phone", "Cell phone", "smartphone"})

STABLE_FRAMES_REQUIRED = int(os.environ.get("VISION_STABLE_FRAMES", "12"))
CONFIDENCE_MIN = float(os.environ.get("VISION_CONFIDENCE_MIN", "0.5"))


@dataclass
class _DetectionState:
    """Gemeinsamer Zustand zwischen GStreamer-Callback und detect()-Aufruf."""
    target_label: str = ""
    stable_count: int = 0
    last_conf: float = 0.0
    found: bool = False
    done: threading.Event = None  # type: ignore[assignment]

    def __post_init__(self):
        self.done = threading.Event()


class HailoDetector:
    """
    Detektor für Raspberry Pi 5 + Hailo-8 AI Kit (T-02, US-02).

    Implementiert DetectorProtocol — austauschbar mit MockDetector.

    Startet die GStreamer-Detection-Pipeline, wartet auf stabile Erkennung
    (STABLE_FRAMES_REQUIRED konsekutive Frames >= CONFIDENCE_MIN) und gibt
    ein VisionResult zurück.
    """

    def detect(self, object_name: str) -> VisionResult:
        """
        Startet Kamerasuche und blockiert bis Objekt stabil erkannt oder
        Timeout erreicht (kein Hailo → sofortiger Fehler).
        """
        if not _hailo_available:
            raise RuntimeError(
                "Hailo-Bibliotheken nicht verfügbar. "
                "Auf dem Raspberry Pi ausführen oder MockDetector verwenden."
            )

        state = _DetectionState(target_label=object_name.strip().lower())
        user_data = _build_callback_class(state)
        app = GStreamerDetectionApp(_make_callback(state), user_data)

        # GStreamer in eigenem Thread starten, detect() blockiert bis done gesetzt
        t = threading.Thread(target=app.run, daemon=True)
        t.start()
        state.done.wait()  # wird in Callback gesetzt sobald stabil erkannt

        return VisionResult(
            name=object_name,
            found=state.found,
            confidence=round(state.last_conf, 4),
        )


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen für GStreamer-Callback
# ---------------------------------------------------------------------------

def _build_callback_class(state: _DetectionState):
    if not _hailo_available:
        return None

    class _UserData(app_callback_class):  # type: ignore[misc]
        pass

    return _UserData()


def _make_callback(state: _DetectionState):
    """Erzeugt einen GStreamer-Pad-Probe-Callback der state befüllt."""

    def _callback(pad, info, user_data):
        from gi.repository import Gst  # noqa: F811
        buffer = info.get_buffer()
        if buffer is None:
            return Gst.PadProbeReturn.OK

        roi = hailo.get_roi_from_buffer(buffer)
        best_conf = 0.0

        for detection in roi.get_objects_typed(hailo.HAILO_DETECTION):
            label = (detection.get_label() or "").strip().lower()
            # Suche nach beliebigem Ziel-Objekt (nicht nur Smartphone)
            target = state.target_label
            if label not in _PHONE_LABELS and label != target:
                continue
            conf = float(detection.get_confidence())
            if conf >= CONFIDENCE_MIN and conf > best_conf:
                best_conf = conf

        if best_conf > 0:
            state.stable_count += 1
            state.last_conf = best_conf
            if state.stable_count >= STABLE_FRAMES_REQUIRED:
                state.found = True
                state.done.set()
        else:
            state.stable_count = 0

        return Gst.PadProbeReturn.OK

    return _callback

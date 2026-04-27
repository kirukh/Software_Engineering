"""HailoDetector — DetectorProtocol-Implementierung für Raspberry Pi 5 + Hailo-8."""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field

from vision_interface import VisionResult

# Hailo-Stack ist nur auf dem Pi installiert — Imports darf auf dem Laptop fehlschlagen.
_hailo_available = False
try:
    import gi
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst
    import hailo
    from hailo_apps.hailo_app_python.apps.detection_simple.detection_pipeline_simple import (
        GStreamerDetectionApp,
    )
    from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import app_callback_class
    _hailo_available = True
except ImportError:
    pass


STABLE_FRAMES_REQUIRED = int(os.environ.get("VISION_STABLE_FRAMES", "12"))
CONFIDENCE_MIN = float(os.environ.get("VISION_CONFIDENCE_MIN", "0.5"))
TIMEOUT_SECONDS = float(os.environ.get("VISION_TIMEOUT", "30"))


@dataclass
class _DetectionState:
    target_label: str = ""
    stable_count: int = 0
    last_conf: float = 0.0
    last_x: float = 0.0
    last_y: float = 0.0
    found: bool = False
    done: threading.Event = field(default_factory=threading.Event)


class HailoDetector:
    def detect(self, object_name: str) -> VisionResult:
        if not _hailo_available:
            raise RuntimeError("Hailo-Bibliotheken nicht verfügbar. Auf dem Pi ausführen.")

        state = _DetectionState(target_label=object_name.strip().lower())

        class _UserData(app_callback_class):
            pass

        app = GStreamerDetectionApp(_make_callback(state), _UserData())
        threading.Thread(target=app.run, daemon=True).start()

        # Timeout: sonst hängt der Aufruf ewig wenn Objekt nie erkannt wird.
        state.done.wait(timeout=TIMEOUT_SECONDS)

        return VisionResult(
            name=object_name,
            found=state.found,
            confidence=round(state.last_conf, 4),
            x=round(state.last_x, 4) if state.found else None,
            y=round(state.last_y, 4) if state.found else None,
        )


def _make_callback(state: _DetectionState):
    """Wird pro Frame aus der GStreamer-Pipeline aufgerufen."""
    def _callback(pad, info, user_data):
        from gi.repository import Gst
        buffer = info.get_buffer()
        if buffer is None:
            return Gst.PadProbeReturn.OK

        roi = hailo.get_roi_from_buffer(buffer)
        best_conf, best_x, best_y = 0.0, 0.0, 0.0

        for det in roi.get_objects_typed(hailo.HAILO_DETECTION):
            label = (det.get_label() or "").strip().lower()
            if label != state.target_label:
                continue
            conf = float(det.get_confidence())
            if conf >= CONFIDENCE_MIN and conf > best_conf:
                bbox = det.get_bbox()
                best_conf, best_x, best_y = conf, bbox.x_center(), bbox.y_center()

        # Treffer muss N Frames in Folge stabil sein → reduziert False Positives.
        if best_conf > 0:
            state.stable_count += 1
            state.last_conf, state.last_x, state.last_y = best_conf, best_x, best_y
            if state.stable_count >= STABLE_FRAMES_REQUIRED:
                state.found = True
                state.done.set()
        else:
            state.stable_count = 0

        return Gst.PadProbeReturn.OK

    return _callback
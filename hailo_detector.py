"""HailoDetector — DetectorProtocol-Implementierung für Pi 5 + Hailo-8."""
from __future__ import annotations

import os
import threading

from vision_interface import FrameCallback, VisionResult

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

# Hinweis: Der Controller liefert immer bereits korrekte COCO-Labels
# (Mapping passiert im Audio-Team). Daher kein Aliasing hier nötig.

CONFIDENCE_MIN = float(os.environ.get("VISION_CONFIDENCE_MIN", "0.5"))


class HailoDetector:
    def prewarm(self) -> None:
        """Hailo lädt erst beim Pipeline-Start — nichts vorzuladen."""
        pass

    def stream(
        self,
        object_name: str,
        on_frame: FrameCallback,
        stop_event: threading.Event,
    ) -> None:
        if not _hailo_available:
            raise RuntimeError("Hailo-Bibliotheken nicht verfügbar. Auf dem Pi ausführen.")

        target = object_name.strip().lower()

        class _UserData(app_callback_class):
            pass

        app = GStreamerDetectionApp(_make_callback(target, object_name, on_frame, stop_event), _UserData())

        # GStreamer in eigenem Thread, damit wir auf stop_event reagieren können.
        threading.Thread(target=app.run, daemon=True).start()
        stop_event.wait()

        # Pipeline sauber stoppen, falls die Hailo-Version es unterstützt.
        try:
            app.shutdown()
        except Exception:
            pass


def _make_callback(target: str, original_name: str, on_frame: FrameCallback, stop_event: threading.Event):
    """Wird pro Frame aus der GStreamer-Pipeline aufgerufen."""
    def _callback(pad, info, user_data):
        from gi.repository import Gst
        if stop_event.is_set():
            return Gst.PadProbeReturn.OK

        buffer = info.get_buffer()
        if buffer is None:
            return Gst.PadProbeReturn.OK

        roi = hailo.get_roi_from_buffer(buffer)
        best_conf, best_x, best_y, best_w, best_h = 0.0, 0.0, 0.0, 0.0, 0.0

        for det in roi.get_objects_typed(hailo.HAILO_DETECTION):
            label = (det.get_label() or "").strip().lower()
            if label != target:
                continue
            conf = float(det.get_confidence())
            if conf >= CONFIDENCE_MIN and conf > best_conf:
                bbox = det.get_bbox()
                best_conf = conf
                best_x, best_y = bbox.x_center(), bbox.y_center()
                best_w, best_h = bbox.width(), bbox.height()

        if best_conf > 0:
            on_frame(VisionResult(
                original_name, True,
                round(best_conf, 4),
                round(best_x, 4), round(best_y, 4),
                round(best_w, 4), round(best_h, 4),
            ))
        else:
            on_frame(VisionResult(original_name, False, 0.0))

        return Gst.PadProbeReturn.OK

    return _callback
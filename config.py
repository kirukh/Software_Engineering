"""
config.py — Zentrale Konfiguration für das Visual-Modul.

Auflösungsreihenfolge (späteres überschreibt früheres):
    1) Defaults aus dem Code (sicher, immer da)
    2) Umgebungsvariablen (VISUAL_*, VISION_*)

Aufruf:
    from config import CONFIG
    print(CONFIG.port, CONFIG.detector_mode)

Aktive Werte ausgeben (zum Debuggen):
    python config.py

Defaults sind so gewählt, dass der Server auf dem Pi out-of-the-box läuft:
- detector_mode = ""  → Auto: probiert Hailo, fällt bei jedem Fehler auf YOLO
  zurück. Damit ist der Sprint-3-Rollout abgesichert, selbst wenn das
  Hailo-Kit zur Laufzeit hakt.
- port = 7995         → mittlere Position der Visual-Range 7991–8000
  (Festlegung Prof. Jehle).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Any


# ------------------------------------------------------------------ Defaults

@dataclass
class VisualConfig:
    """Alle Tuning-Parameter des Visual-Moduls an einer Stelle.

    Range-Hinweis: Port-Range Visual ist 7991–8000 (Festlegung Prof. Jehle).
    """

    # --- Server ---
    host: str = "127.0.0.1"      # 0.0.0.0 für Netzwerk-Zugriff von anderen Geräten
    port: int = 7995             # in Range 7991–8000

    # --- Detector-Wahl ---
    # "" = Auto (Hailo bevorzugt, Fallback YOLO) — Default für Pi-Rollout.
    # "hailo" = nur Hailo, kein Fallback (für Performance-Messungen).
    # "yolo"  = nur YOLO + Webcam (Laptop-Tests).
    detector_mode: str = ""

    # --- Detection-Parameter ---
    confidence_min: float = 0.5  # pro Frame
    window_size: int = 8         # Sliding-Window-Größe in Frames
    min_hits_in_window: int = 5  # Mindesttreffer für found=True

    # --- YOLO-spezifisch ---
    camera_index: int = 0        # Webcam-Index
    model_path: str = "yolov8n.pt"

    # --- Timing ---
    stop_timeout_seconds: float = 5.0  # Wait beim Tracking-Stop

    def validate(self) -> None:
        """Plausibilitäts-Checks. Wirft ValueError bei Quatsch."""
        if not (7991 <= self.port <= 8000):
            raise ValueError(
                f"port={self.port} außerhalb der Visual-Range 7991–8000. "
                f"Wenn das Absicht ist, passe die Range im config.py an."
            )
        if self.detector_mode not in ("", "hailo", "yolo"):
            raise ValueError(
                f"detector_mode={self.detector_mode!r} ungültig. "
                f"Erlaubt: '' (auto), 'hailo', 'yolo'."
            )
        if not (0.0 <= self.confidence_min <= 1.0):
            raise ValueError(f"confidence_min={self.confidence_min} muss in [0.0, 1.0] liegen")
        if self.window_size < 1:
            raise ValueError(f"window_size={self.window_size} muss >= 1 sein")
        if not (1 <= self.min_hits_in_window <= self.window_size):
            raise ValueError(
                f"min_hits_in_window={self.min_hits_in_window} muss in "
                f"[1, window_size={self.window_size}] liegen"
            )
        if self.camera_index < 0:
            raise ValueError(f"camera_index={self.camera_index} muss >= 0 sein")
        if self.stop_timeout_seconds <= 0:
            raise ValueError(f"stop_timeout_seconds={self.stop_timeout_seconds} muss > 0 sein")


# ------------------------------------------------------------------ Env-Mapping

# Feldname → Env-Variable. Praktisch zum kurzfristigen Überschreiben:
#   VISUAL_PORT=7996 python server.py
_ENV_MAP: dict[str, str] = {
    "host": "VISUAL_HOST",
    "port": "VISUAL_PORT",
    "detector_mode": "VISUAL_DETECTOR",
    "confidence_min": "VISION_CONFIDENCE_MIN",
    "window_size": "VISION_WINDOW_SIZE",
    "min_hits_in_window": "VISION_MIN_HITS_IN_WINDOW",
    "camera_index": "VISION_CAMERA_INDEX",
    "model_path": "VISION_MODEL_PATH",
    "stop_timeout_seconds": "VISION_STOP_TIMEOUT_SECONDS",
}


def _coerce(value: Any, target_type: type) -> Any:
    """String → richtigen Typ. Wird für Env-Variablen gebraucht."""
    if value is None:
        return None
    if target_type is bool:
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    return str(value)


# ------------------------------------------------------------------ Build

def load_config() -> VisualConfig:
    """Config zusammenbauen: Defaults < Env-Variablen."""
    cfg = VisualConfig()

    for name, env_var in _ENV_MAP.items():
        raw = os.environ.get(env_var)
        if raw is None:
            continue
        default_val = getattr(cfg, name)
        try:
            setattr(cfg, name, _coerce(raw, type(default_val)))
        except (ValueError, TypeError) as e:
            print(f"[config] Env {env_var}={raw!r} ungültig: {e} — Default beibehalten.")

    # detector_mode normalisieren (lower, leerstring statt None)
    cfg.detector_mode = (cfg.detector_mode or "").strip().lower()

    cfg.validate()
    return cfg


# Modulweite Instanz — wird beim ersten Import gebaut.
CONFIG: VisualConfig = load_config()


# ------------------------------------------------------------------ Debug-Helper

def _print_config() -> None:
    print("Aktive Visual-Konfiguration:")
    for k, v in asdict(CONFIG).items():
        env = _ENV_MAP.get(k, "—")
        print(f"  {k:25s} = {v!r:25s}  (Env: {env})")


if __name__ == "__main__":
    _print_config()
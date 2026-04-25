"""
visual.py — Schnittstelle des Visual-Moduls.

Der Controller ruft uns direkt im Prozess auf (kein HTTP). Wir bieten:
    search(request)          # blockierend, einfacher Convenience-Pfad
    start_search(request)    # startet Suche im Hintergrund, gibt job_id
    get_result(job_id)       # pollt Status / Ergebnis
    cancel(job_id)           # bricht laufende Suche ab

Dict-Format:
    rein  → {"name": "smartphone"}
    raus  → {"name": str, "found": bool, "confidence": float,
             "x": float|None, "y": float|None}

Detector-Wahl per VISUAL_DETECTOR=hailo|yolo (sonst Auto: Hailo > YOLO).
"""
from __future__ import annotations

import os
import threading
import time
import uuid

from vision_interface import DetectorProtocol, VisionResult

_detector: DetectorProtocol | None = None
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


# ------------------------------------------------------------------ Detector

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


# ------------------------------------------------------------------ Hilfsfunktionen

def _extract_name(request: dict) -> str:
    if not isinstance(request, dict):
        raise ValueError(f"request muss ein dict sein, bekam: {type(request).__name__}")
    name = request.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"request['name'] muss ein nicht-leerer String sein, bekam: {name!r}")
    return name.strip()


# ------------------------------------------------------------------ Sync-API

def search(request: dict) -> dict:
    """Blockierende Suche — einfacher Pfad für Tests und einfache Aufrufer."""
    name = _extract_name(request)
    return _get_detector().detect(name).to_dict()


# ------------------------------------------------------------------ Async-API
# Hauptpfad für den Controller: Suche im Hintergrund-Thread, abbrechbar.

def start_search(request: dict) -> dict:
    name = _extract_name(request)
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "result": None}
    threading.Thread(target=_run_job, args=(job_id, name), daemon=True).start()
    return {"job_id": job_id, "status": "running"}


def get_result(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return {"status": "unknown", "error": "job_id nicht gefunden"}
    if job["status"] == "running":
        return {"status": "running"}
    if job["status"] == "done":
        return {"status": "done", **job["result"]}
    # cancelled oder error
    return {"status": job["status"], **({"message": job["result"]} if job["status"] == "error" else {})}


def cancel(job_id: str) -> dict:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return {"status": "unknown", "error": "job_id nicht gefunden"}
        if job["status"] == "running":
            job["status"] = "cancelled"
    return {"status": "cancelled", "job_id": job_id}


def _run_job(job_id: str, name: str) -> None:
    """Worker-Thread: nutzt sync search() intern, schreibt Ergebnis in _jobs."""
    try:
        result = search({"name": name})
        with _jobs_lock:
            job = _jobs.get(job_id)
            # Cancel zwischenzeitlich? Dann Ergebnis verwerfen.
            if job and job["status"] == "running":
                job["status"] = "done"
                job["result"] = result
    except Exception as e:
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["result"] = str(e)
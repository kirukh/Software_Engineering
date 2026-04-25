# Visual Team — README

Objekterkennung über Kamera + KI auf dem Raspberry Pi 5 + Hailo-8.
Wird vom Controller per direktem Funktionsaufruf im selben Prozess genutzt.

## Schnittstelle

**Datei:** `visual.py`

**Synchron** (einfach, blockierend):
```python
from visual import search

search({"name": "smartphone"})
# → {"name": "smartphone", "found": True, "confidence": 0.92, "x": 0.51, "y": 0.48}
```

**Asynchron** (Hauptpfad für den Controller, mit Cancel-Möglichkeit):
```python
from visual import start_search, get_result, cancel

job = start_search({"name": "smartphone"})  # → {"job_id": "...", "status": "running"}
get_result(job["job_id"])                   # → {"status": "running"} oder Ergebnis-Dict
cancel(job["job_id"])                       # bricht laufende Suche ab
```

## Detector-Auswahl

Per Umgebungsvariable `VISUAL_DETECTOR`:

| Wert | Verhalten |
|------|-----------|
| `hailo` | HailoDetector (Pi 5 + Hailo-8) |
| `yolo` | YoloDetector (Webcam + YOLOv8, ohne Hailo testbar) |
| *(nicht gesetzt)* | Auto: Hailo wenn verfügbar, sonst YOLO |

Weitere Tuning-Variablen: `VISION_STABLE_FRAMES`, `VISION_CONFIDENCE_MIN`, `VISION_TIMEOUT`, `VISION_CAMERA_INDEX`, `VISION_MODEL_PATH`.

## Architektur-Entscheidung: kein REST

Beide Module (Controller + Visual) laufen fest verbaut im selben Prozess auf dem
Pi. Ein direkter Funktionsaufruf ist einfacher zu debuggen, schneller und
vermeidet unnötigen Netzwerk-Layer.

## Tests

```bash
python test_visual.py           # Fake-Tests, ohne Hardware
python test_visual.py --live    # zusätzlich: echte Webcam, echtes Smartphone
```

## Anforderungen

| ID | Anforderung |
|---|---|
| FR-01 | Suchanfragen als Dict vom Controller akzeptieren |
| FR-02 | Bilder von der Kamera-Hardware erfassen |
| FR-03 | KI-gestützte Bildanalyse durchführen |
| FR-04 | Dict mit `name`, `found`, `confidence`, `x`, `y` zurückgeben |
| ITF-01 | Suchanfragen vom Controller per Funktionsaufruf empfangen |
| ITF-02 | Ergebnis-Dict an Controller zurückgeben |
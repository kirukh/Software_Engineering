# Visual Team — README

Objekterkennung über Kamera + KI auf dem Raspberry Pi 5 + Hailo-8.
Stellt dem Controller eine HTTP-API bereit, die kontinuierlich Tracking-Ergebnisse
liefert ("Dauerfeuer"). Controller pollt das aktuelle aggregierte Ergebnis.

**Quick Start für Controller-Team:** siehe [`Anleitung.md`](Anleitung.md).

## Architektur

```
                        ┌──────────────────────────────────┐
  Controller            │  Visual-Server (FastAPI :7995)   │
  ─────────             │  ────────────────────            │
  POST /track/start ───▶│  visual.start_tracking()         │
  GET  /track/latest ──▶│  visual.get_latest()             │
  POST /track/stop  ───▶│  visual.stop_tracking()          │
  GET  /health      ───▶│  status + aktiver Detector       │
                        │                                  │
                        │  Hintergrund-Thread:             │
                        │  Detector.stream() → on_frame ───┼──▶ Sliding Window
                        │                                  │    (8 Frames)
                        └──────────────────────────────────┘
                                       │
                                       ▼
                          ┌─────────────────────────┐
                          │ Auto-Wahl:              │
                          │  1) HailoDetector       │
                          │  2) YoloDetector (Fall.)│
                          └─────────────────────────┘
```

Detector liefert pro Frame ein Roh-Ergebnis. `visual.py` hält ein **Sliding
Window** der letzten N Frames (Default 8) und aggregiert beim Polling: bei
mind. M Treffern (Default 5) → `found=True` mit Mittelwerten von
`confidence`, `x`, `y`, `w`, `h`. Sonst `found=False` mit allen Koordinaten
auf `null`.

## Konfiguration

Alle Parameter liegen in `config.py` als `VisualConfig`-Dataclass.

**Zwei Ebenen, später hat Vorrang:**
1. Defaults im Code (`config.py`)
2. Umgebungsvariablen (zum kurzfristigen Überschreiben)

Aktive Werte anzeigen:
```bash
python config.py
```

Beispielausgabe:
```
Aktive Visual-Konfiguration:
  host                      = '127.0.0.1'                (Env: VISUAL_HOST)
  port                      = 7995                       (Env: VISUAL_PORT)
  detector_mode             = ''                         (Env: VISUAL_DETECTOR)
  confidence_min            = 0.5                        (Env: VISION_CONFIDENCE_MIN)
  ...
```

| Feld | Default | Env-Variable | Bedeutung |
|---|---|---|---|
| `host` | `127.0.0.1` | `VISUAL_HOST` | Server-Bind. `0.0.0.0` für externen Zugriff |
| `port` | `7995` | `VISUAL_PORT` | Server-Port (Range 7991–8000) |
| `detector_mode` | `""` (auto) | `VISUAL_DETECTOR` | `"hailo"`, `"yolo"`, oder leer für Auto |
| `confidence_min` | `0.5` | `VISION_CONFIDENCE_MIN` | Mindest-Konfidenz pro Frame |
| `window_size` | `8` | `VISION_WINDOW_SIZE` | Sliding-Window-Größe |
| `min_hits_in_window` | `5` | `VISION_MIN_HITS_IN_WINDOW` | Mindesttreffer für `found=true` |
| `camera_index` | `0` | `VISION_CAMERA_INDEX` | Webcam-Index (nur YOLO) |
| `model_path` | `yolov8n.pt` | `VISION_MODEL_PATH` | YOLO-Modell-Pfad |
| `stop_timeout_seconds` | `5.0` | `VISION_STOP_TIMEOUT_SECONDS` | Wait beim Tracking-Stop |

**Werte dauerhaft ändern:** direkt in `config.py` editieren.
**Werte für einen einzelnen Lauf ändern:** Env-Variable vor dem Aufruf setzen, z.B.
```bash
VISUAL_PORT=7996 python server.py
```

## HTTP-API

### `POST /track/start`
```json
Request:  {"name": "cell phone"}
Response: {"status": "running", "name": "cell phone"}
```

### `GET /track/latest`
```json
// Tracking läuft, Objekt erkannt
{"status": "running", "name": "cell phone", "found": true,
 "confidence": 0.87, "x": 0.51, "y": 0.48, "w": 0.18, "h": 0.32}

// Tracking läuft, Objekt nicht (mehr) erkannt
{"status": "running", "name": "cell phone", "found": false,
 "confidence": 0.0, "x": null, "y": null, "w": null, "h": null}

// Kein Tracking aktiv
{"status": "idle"}
```

### `POST /track/stop`
```json
Response: {"status": "stopped", "was_running": true}
```

### `GET /health`
```json
Response: {"status": "ok", "detector": "hailo"}
```
`detector` kann `"hailo"`, `"yolo"` oder `"none"` (vor Prewarm) sein —
hilfreich um zu sehen, ob im Auto-Modus der Fallback gegriffen hat.

## Server starten

```bash
# Auto-Detector (Hailo wenn verfügbar, sonst YOLO) — Default
python server.py

# YOLO-Webcam erzwingen (Laptop ohne Hailo)
VISUAL_DETECTOR=yolo python server.py

# Hailo erzwingen (kein Fallback, fail wenn nicht da)
VISUAL_DETECTOR=hailo python server.py

# Netzwerk-Zugriff von anderen Geräten erlauben
VISUAL_HOST=0.0.0.0 python server.py
```

## Fallback-Verhalten

| Konfiguration | Hailo OK | Hailo kaputt |
|---|---|---|
| `detector_mode` leer (Auto) | nutzt Hailo | fällt auf YOLO, Server läuft |
| `detector_mode=hailo` | nutzt Hailo | Server-Start failed |
| `detector_mode=yolo` | nutzt YOLO | nutzt YOLO |

Sprint-Ziel ist "Rollout muss laufen" — der Auto-Modus stellt das sicher.
Wenn ihr explizit Hailo *messen* wollt (z.B. Inferenz-Performance), nutzt den
expliziten Modus, damit ein Fallback nicht stillschweigend passiert.

## Polling-Beispiel (Controller-Seite)

```python
from visual_client import VisualClient
import time

with VisualClient() as visual:
    visual.start("cell phone")  # COCO-Label, vom Audio-Team geliefert
    while controller_running:
        r = visual.latest()
        if r["status"] == "running" and r["found"]:
            laser.point_to(r["x"], r["y"])
        else:
            laser.idle()
        time.sleep(0.1)
```

> **Wichtig:** `name` muss ein gültiges COCO-Label sein (z.B. `"cell phone"`,
> `"person"`, `"bottle"`), nicht ein Umgangs-Begriff wie `"smartphone"` oder
> `"handy"`. Das Audio-Team mappt Sprache auf COCO-Labels, bevor es zum
> Controller geht. `coco.yaml` ist die geteilte Source-of-Truth.

## Tests

```bash
python config.py                 # aktive Config anzeigen
python test_visual.py            # Fake-Tests, ohne Hardware
python test_visual.py --server   # zusätzlich HTTP-Endpoints (mit Fake)
python live_e2e_test.py          # interaktiver Webcam-Test (YOLO), Default cell phone 30s
```

## Architektur-Entscheidung: HTTP-Server (Sprint 2)

In Sprint 1 hatten wir uns gegen REST entschieden (einmaliger Aufruf, kein
Netzwerk-Layer nötig). In Sprint 2 wurde die Anforderung geändert:
**kontinuierliches Tracking** ("Dauerfeuer") für den Laserpointer.
Optionen waren:

- Eigener OS-Prozess + IPC (Pipe/Socket) — komplex, schwer zu debuggen
- Server-Sent-Events — eine Sonderlocke ggü. den anderen Teams
- **HTTP-Polling — gewählt:** einheitlich mit den anderen Teams, mit `curl`
  trivial zu debuggen, FastAPI + Pydantic passt direkt zu unserem Code

## Anforderungen

| ID | Anforderung |
|---|---|
| FR-01 | Suchanfragen (Objektname) per HTTP vom Controller akzeptieren |
| FR-02 | Bilder von der Kamera-Hardware kontinuierlich erfassen |
| FR-03 | KI-gestützte Bildanalyse pro Frame durchführen |
| FR-04 | Ergebnis mit `name`, `found`, `confidence`, `x`, `y`, `w`, `h` zurückgeben |
| FR-05 | Sliding-Window-Aggregation über N Frames für stabile Ausgabe |
| FR-06 | Auto-Fallback Hailo → YOLO, damit Rollout auch ohne funktionierendes AI Kit läuft |
| FR-07 | Zentrale Konfiguration (`config.py`) mit Env-Override |
| ITF-01 | HTTP-API: `POST /track/start`, `GET /track/latest`, `POST /track/stop` |
| ITF-02 | JSON-Antworten, Pydantic-validiert |
| ITF-03 | `GET /health` liefert aktiven Detector zurück (zum Debuggen) |
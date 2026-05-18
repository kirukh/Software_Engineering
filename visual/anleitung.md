# Anleitung: Visual-Server starten & einbinden

Diese Anleitung erklärt, wie der Visual-Server auf dem Pi gestartet wird und wie ihr (Controller-Team) ihn aus eurem Code anspricht. Sprint-Ziel: Roboter findet ein vom Audio-Team gemeldetes Objekt und liefert die Koordinaten zurück.

## TL;DR für das Controller-Team

```python
from visual_client import VisualClient

with VisualClient(base_url="http://127.0.0.1:7995") as visual:
    visual.start("cell phone")          # COCO-Label vom Audio-Team
    while suche_läuft:
        r = visual.latest()
        if r["status"] == "running" and r["found"]:
            # Treffer! r["x"], r["y"], r["w"], r["h"] sind 0.0–1.0
            controller.handle_found(r)
            break
        time.sleep(0.1)
    # stop() wird automatisch beim Verlassen aufgerufen
```

Das ist alles. Details unten.

---

## 1. Vorbereitung auf dem Pi

### 1.1 Repo + Dependencies

```bash
git clone <unser-repo>
cd visual/
pip install -r requirements-laptop.txt
```

Auf dem Pi ist zusätzlich der Hailo-Stack installiert (das macht der Pi-Setup-Script vom Team — fragt Christian, wenn das auf einem frischen Pi gemacht werden muss).

### 1.2 YOLO-Modell laden (Fallback)

Beim ersten YOLO-Start zieht `ultralytics` das `yolov8n.pt`-Modell von sich aus runter. Das dauert kurz, ist aber einmalig. Wenn das Pi später offline laufen soll, einmal vorab online starten.

### 1.3 Config prüfen

```bash
python config.py
```

Zeigt die aktiven Werte. Falls etwas nicht stimmt: über Env-Variablen (z.B. `VISUAL_PORT=7996 python server.py`) oder über eine `config.yaml` anpassen (siehe Abschnitt 7).

## 2. Server starten

### Standardfall (alles auf dem Pi)

```bash
python server.py
```

Der Server lauscht auf `127.0.0.1:7995` und nimmt automatisch den besten Detector: Hailo, wenn das AI-Kit funktioniert, sonst YOLO als Fallback. Beim Start steht in der Konsole, welcher Detector aktiv ist.

### Andere Geräte sollen zugreifen können

Wenn der Controller (oder das Audio-Team) auf einem anderen Gerät läuft und über Netzwerk auf den Pi zugreift:

```bash
VISUAL_HOST=0.0.0.0 python server.py
```

Damit ist der Server unter `http://<pi-ip>:7995` aus dem lokalen Netzwerk erreichbar.

### Detector erzwingen

| Befehl | Effekt |
|---|---|
| `python server.py` | Auto: Hailo, fallback auf YOLO |
| `VISUAL_DETECTOR=hailo python server.py` | Nur Hailo, fail wenn nicht verfügbar |
| `VISUAL_DETECTOR=yolo python server.py` | Nur YOLO (Webcam, auch ohne Hailo-Kit) |

## 3. HTTP-API

Base URL: `http://127.0.0.1:7995` (oder `http://<pi-ip>:7995` bei `VISUAL_HOST=0.0.0.0`).

### `POST /track/start`

```http
POST /track/start
Content-Type: application/json

{"name": "cell phone"}
```

→ `{"status": "running", "name": "cell phone"}`

**Wichtig:** `name` muss ein **gültiges COCO-Label** sein. Das Audio-Team mappt natürliche Sprache → COCO. Wir nehmen den Wert hier 1:1, ohne weiteres Mapping. Liste der COCO-Klassen: siehe `coco.yaml` (Single Source of Truth zwischen Audio- und Visual-Team).

Idempotent:
- Aufruf mit demselben Namen während Tracking läuft → no-op
- Aufruf mit anderem Namen → altes Tracking wird gestoppt, neues gestartet

### `GET /track/latest`

Aktuelles aggregiertes Ergebnis aus dem Sliding Window der letzten 8 Frames. Status-abhängig drei Formen:

**Kein Tracking aktiv:**
```json
{"status": "idle"}
```

**Tracking läuft, aktuell nichts erkannt:**
```json
{
  "status": "running", "name": "cell phone", "found": false,
  "confidence": 0.0, "x": null, "y": null, "w": null, "h": null
}
```

**Tracking läuft, Treffer:**
```json
{
  "status": "running", "name": "cell phone", "found": true,
  "confidence": 0.87,
  "x": 0.51, "y": 0.48,
  "w": 0.18, "h": 0.32
}
```

Alle Koordinaten sind auf 0.0–1.0 normiert (Bruchteile des Bildes, nicht Pixel).

### `POST /track/stop`

```http
POST /track/stop
```

→ `{"status": "stopped", "was_running": true}`

Idempotent — Aufruf ohne laufendes Tracking gibt `was_running: false`.

### `GET /health`

```http
GET /health
```

→ `{"status": "ok", "detector": "hailo"}`

`detector` ist `"hailo"`, `"yolo"`, oder `"none"` (Server noch nicht geprewarmt). Praktisch, um schnell zu prüfen, ob der Pi gerade Hailo oder Fallback fährt.

## 4. Integration in den Controller

### Option A: `visual_client.py` direkt nutzen (empfohlen)

`visual_client.py` ist eine fertige Python-Bibliothek, die alle Endpoints kapselt. Einfach in eurem Repo importieren:

```python
from visual_client import VisualClient
import time

with VisualClient(base_url="http://127.0.0.1:7995") as visual:
    # Healthcheck beim Verbinden:
    if not visual.health():
        raise RuntimeError("Visual-Server nicht erreichbar")

    # Tracking starten (Label vom Audio-Team):
    visual.start("cell phone")

    # Polling-Loop:
    while controller_state == "searching":
        r = visual.latest()
        if r["status"] == "running" and r["found"]:
            # → an Navigation/Laser weitergeben
            handle_found(r["x"], r["y"], r["w"], r["h"], r["confidence"])
            break
        time.sleep(0.1)

    # stop() wird vom Context-Manager automatisch gerufen
```

### Option B: Roh-HTTP via `httpx`/`requests`

Wenn ihr keinen Python-Import wollt (z.B. weil ihr in einer anderen Sprache schreibt), geht alles auch direkt per HTTP. Beispiel mit `curl`:

```bash
# Tracking starten
curl -X POST http://127.0.0.1:7995/track/start \
     -H "Content-Type: application/json" \
     -d '{"name": "cell phone"}'

# Pollen
curl http://127.0.0.1:7995/track/latest

# Stoppen
curl -X POST http://127.0.0.1:7995/track/stop
```

## 5. Polling-Verhalten

- **Empfohlene Polling-Rate: 100 ms.** Schneller bringt nichts, weil das Sliding Window erst alle ~250 ms (Hailo) bzw. ~500 ms (YOLO) ein neues aggregiertes Ergebnis liefert.
- **Polling ist günstig** — nur ein HTTP GET, keine Berechnung serverseitig (das Window läuft im Hintergrund eh durch).
- **`found=True` ist stabil**: Mindestens 5 von 8 Frames im Fenster müssen das Objekt erkannt haben. Das filtert YOLO-/Hailo-Jitter raus.

## 6. Typische Probleme

| Symptom | Vermutliche Ursache |
|---|---|
| `httpx.ConnectError` | Server nicht gestartet, oder falscher Host/Port |
| Connection refused von anderem Gerät | `VISUAL_HOST=127.0.0.1` (Default) blockt von außen. Mit `VISUAL_HOST=0.0.0.0` starten |
| `found` wird nie `true` | (1) Falsches Label — `"smartphone"` statt `"cell phone"`. (2) Objekt nicht im Sichtfeld. (3) Konfidenz zu niedrig — `confidence_min` in der Config runtersetzen |
| `/health` antwortet `detector: yolo` obwohl Hailo da sein soll | Hailo-Init schlug fehl, Fallback griff. Logs im Server-Terminal checken |
| Erster `/track/start` braucht 10–30s | Normal: YOLO lädt das Modell. Mit Prewarm im Server-Start schon erledigt, sollte beim zweiten Mal schnell sein |
| `ModuleNotFoundError: vision_interface` | Datei wurde in `visual_interface.py` umbenannt — zurück auf `vision_interface.py` |

## 7. Konfiguration

Alle Tuning-Parameter liegen in `config.py`. Drei Ebenen (späteres überschreibt früheres):

1. **Defaults** im Code
2. **`config.yaml`** im Repo-Root (optional)
3. **Env-Variablen**

### Alle Felder

| Feld | Default | Env | Erlaubte Werte |
|---|---|---|---|
| `host` | `127.0.0.1` | `VISUAL_HOST` | IP oder Hostname |
| `port` | `7995` | `VISUAL_PORT` | 7991–8000 |
| `detector_mode` | `""` | `VISUAL_DETECTOR` | `""`, `"hailo"`, `"yolo"` |
| `confidence_min` | `0.5` | `VISION_CONFIDENCE_MIN` | 0.0–1.0 |
| `window_size` | `8` | `VISION_WINDOW_SIZE` | ≥ 1 |
| `min_hits_in_window` | `5` | `VISION_MIN_HITS_IN_WINDOW` | 1–window_size |
| `camera_index` | `0` | `VISION_CAMERA_INDEX` | ≥ 0 |
| `model_path` | `yolov8n.pt` | `VISION_MODEL_PATH` | Pfad |
| `stop_timeout_seconds` | `5.0` | `VISION_STOP_TIMEOUT_SECONDS` | > 0 |

### `config.yaml` verwenden

```bash
cp config.yaml.example config.yaml
pip install pyyaml
nano config.yaml         # eigene Werte eintragen
python config.py         # checken dass die Werte angenommen wurden
python server.py
```

Env-Variablen überschreiben `config.yaml` — praktisch fürs Debuggen:
```bash
VISUAL_PORT=7996 python server.py   # ein einzelner Lauf auf anderem Port
```

## 8. Lokal testen (ohne Pi)

Wenn ihr eure Controller-Integration auf dem Laptop testen wollt, könnt ihr unseren Server mit YOLO + Webcam laufen lassen:

```bash
VISUAL_DETECTOR=yolo python server.py
```

Dann gegen `http://127.0.0.1:7995` arbeiten. COCO-Label `"person"` ist am zuverlässigsten zum Probieren — einfach in die Webcam gucken.

## 9. Bekannte offene Punkte

- **Video-Stream-Endpoint** (`GET /stream` o.ä.) ist für Sprint 4 angedacht, noch nicht implementiert.
- **Team-übergreifende Config-Datei** (alle Modul-Ports an einer Stelle): in Diskussion. Aktuell nur Visual.

Bei Fragen oder Problemen: Slack-Channel `#team-visual` oder direkt Christian.
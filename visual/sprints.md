# Team Visual — Sprint README

> Sprint-Länge: **1 Woche** | Hardware: **Raspberry Pi 5 + Hailo-8 AI Kit**
> Zentrale Schnittstelle: **HTTP-API** (`/track/start`, `/track/latest`, `/track/stop`)

---

## Rückblick auf alle Sprints

| Sprint | Zeitraum | Ziel | Status |
|--------|----------|------|--------|
| Sprint 1 | KW 17 – KW 18 | `search()` mit Hailo + YOLO-Fallback | ✅ Done |
| Sprint 2 | KW 18 – KW 19 | Tracking-Server mit Sliding-Window-Aggregation | 🔄 In Progress |

---

## Sprint 2

**Zeitraum:** KW 18 – KW 19 (28.04.2026 – 04.05.2026)

### Sprint Goal
Umstellung von einmaligem `search()` auf kontinuierliches **Tracking**:
Detector läuft im Hintergrund, schiebt jeden Frame in ein Sliding Window,
Controller pollt das aktuelle aggregierte Ergebnis per HTTP. Das Ergebnis
enthält zusätzlich zur Position (`x`, `y`) jetzt auch die Größe (`w`, `h`),
damit der Laserpointer das Ziel besser ansteuern kann.

### Architektur-Entscheidungen im Sprint

1. **HTTP-Server statt In-Process-Aufruf.** In Sprint 1 hatten wir REST
   abgelehnt. Mit der neuen Anforderung "Dauerfeuer" macht ein Server jetzt
   Sinn: Polling ist einheitlich mit den anderen Teams und einfach zu
   debuggen (`curl`).
2. **Polling statt SSE/WebSocket.** Polling alle 100ms ist für den Laser
   ausreichend, deutlich einfacher zu implementieren, und der Controller
   kann sein Pattern für alle Teams wiederverwenden.
3. **Sliding Window über die letzten 8 Frames** statt jedes Frame einzeln
   rauszugeben. Glättet Jitter, reduziert HTTP-Last, der Laser bleibt ruhiger.

### User Stories

| ID | Story | Akzeptanzkriterium | SP |
|----|-------|--------------------|----|
| US-05 | Detector im Streaming-Modus statt blockierend. | `stream(name, on_frame, stop_event)` läuft bis zum Stop. | 3 |
| US-06 | Sliding-Window-Aggregation über N Frames. | Mind. M Treffer im Fenster → `found=True` mit Mittelwerten. | 2 |
| US-07 | HTTP-API für den Controller. | `POST /track/start`, `GET /track/latest`, `POST /track/stop`. | 3 |
| US-08 | Bounding-Box-Größe (`w`, `h`) im Ergebnis. | Zusätzlich zu `x`, `y` normiert auf 0.0–1.0. | 1 |

**Gesamt: 9 Story Points**

### Sprint Backlog

| ID | Task | Story | SP | Status |
|----|------|-------|----|--------|
| T-08 | `DetectorProtocol.stream()` + `w`/`h` in `VisionResult` | US-05/08 | 1 | ✅ Done |
| T-09 | `YoloDetector.stream()` umbauen, w/h liefern | US-05/08 | 2 | ✅ Done |
| T-10 | `HailoDetector.stream()` umbauen, w/h liefern | US-05/08 | 2 | ⏳ Open (Pi-Test) |
| T-11 | `visual.py`: Tracking-API + Sliding-Window-Aggregation | US-06 | 2 | ✅ Done |
| T-12 | `server.py`: FastAPI mit `/track/*` Endpoints | US-07 | 1 | ✅ Done |
| T-13 | `test_visual.py`: Fake- und Server-Tests, `live_e2e_test.py` | US-05/06/07 | 1 | ✅ Done |

### Definition of Ready

- Anforderung "Dauerfeuer" ist mit Controller- und Laser-Team abgestimmt
- HTTP vs. SSE-Entscheidung ist getroffen
- Sliding-Window-Parameter (Größe, Mindesttreffer) sind sinnvoll defaultet
- Architektur-Wechsel ist im Team begründet (nicht nur "machen wir mal")

### Definition of Done

- Tests grün auf dem Laptop (Fake + Server + Live-E2E)
- Auf dem Pi getestet (Hailo-Stream)
- Controller-Team kann gegen den Server pollen und sinnvolle Werte bekommen
- README beschreibt die HTTP-API und den Polling-Flow
- `w`/`h` durch alle Schichten konsistent
- Alte API (`search`/`start_search`/`get_result`/`cancel`) ist entfernt — keine
  Legacy-Pfade

### Offene Punkte

- **Hailo-Live-Test auf dem Pi** noch ausstehend.
- **Stop-Verhalten von GStreamer** (`app.shutdown()`) muss am echten Hailo
  geprüft werden — die Methode existiert ggf. nicht so, ein Fallback über
  Pipeline-State `Gst.State.NULL` könnte nötig sein.
- **Zentrale Config-Datei** wurde im Daily diskutiert, aber noch nicht
  umgesetzt — derzeit alles weiterhin per Env-Variable. Vorschlag: Sprint 3.
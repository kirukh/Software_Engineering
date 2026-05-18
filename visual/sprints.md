# Team Visual — Sprint README

> Sprint-Länge: **1 Woche** | Hardware: **Raspberry Pi 5 + Hailo-8 AI Kit**
> Zentrale Schnittstelle: **HTTP-API** (`/track/start`, `/track/latest`, `/track/stop`)
> Default-Port: **7995** (Visual-Range 7991–8000)

---

## Rückblick auf alle Sprints

| Sprint | Zeitraum | Ziel | Status |
|--------|----------|------|--------|
| Sprint 1 | KW 17 – KW 18 | `search()` mit Hailo + YOLO-Fallback | ✅ Done |
| Sprint 2 | KW 18 – KW 19 | Tracking-Server mit Sliding-Window-Aggregation | ✅ Done |
| Sprint 3 | KW 19 – KW 20 | Full Rollout auf dem Pi + End-to-End mit allen Teams | 🔄 In Progress |

---

## Sprint 3 (aktuell)

**Zeitraum:** KW 19 – KW 20 (05.05.2026 – 11.05.2026)

### Sprint Goal
**End-to-End-Rollout auf dem Pi**: Audio-Team sendet COCO-Label → Controller
ruft Visual auf → Visual findet das Objekt und liefert die Koordinaten zurück.
Egal ob Hailo oder YOLO unter der Haube läuft, der Rollout muss
funktionieren.

### Architektur-Entscheidungen im Sprint

1. **Port-Festlegung 7995** in der Visual-Range 7991–8000 (Prof. Jehle hat
   die Ranges in KW 19 verteilt). Mittlerer Wert in der Range, damit später
   noch Platz für einen Video-Stream-Endpoint o.ä. ist.
2. **Auto-Fallback Hailo → YOLO** als hartes Sprint-Requirement: wenn das
   Hailo-Kit zur Laufzeit nicht initialisieren kann, fällt der Server
   stillschweigend (mit Log) auf YOLO zurück. Begründung: der Rollout darf
   nicht an einer wackeligen Hailo-Init scheitern. Wer explizit Hailo *will*
   (für Performance-Tests), setzt `VISUAL_DETECTOR=hailo` und kriegt einen
   harten Fehler.
3. **GET /health liefert aktiven Detector zurück** — kleine Erweiterung,
   damit das Controller-Team auf einen Blick sieht, ob im Auto-Modus
   Hailo oder Fallback aktiv ist.
4. **`VISUAL_HOST` konfigurierbar** (Default `127.0.0.1`). Für Single-Pi-
   Rollout reicht der Default; wenn der Audio-Laptop später extern zugreifen
   soll, `VISUAL_HOST=0.0.0.0`.

### User Stories

| ID | Story | Akzeptanzkriterium | SP |
|----|-------|--------------------|----|
| US-09 | Visual-Port liegt in der zugewiesenen Range (7991–8000). | Default-Port = 7995 in allen Files konsistent. | 1 |
| US-10 | Server läuft auch ohne funktionierendes Hailo-Kit. | Auto-Modus fällt bei Hailo-Fehler auf YOLO zurück, Server startet, `/health` zeigt aktiven Detector. | 2 |
| US-11 | Hailo-Path auf dem Pi getestet (T-10 aus Sprint 2 nachgezogen). | `live_e2e_test.py` läuft mit Hailo auf dem Pi, Treffer für mind. ein COCO-Label. | 3 |
| US-12 | Controller-Team kann uns ohne Rückfragen einbinden. | `Anleitung.md` ist vorhanden, deckt Start, API und Polling-Pattern ab. | 1 |
| US-13 | End-to-End: Audio → Controller → Visual → Controller → Aktion. | Joint-Test-Session: gesprochenes Objekt löst Detection aus, Controller bekommt sinnvolle Koordinaten. | 3 |

**Gesamt: 10 Story Points**

### Sprint Backlog

| ID | Task | Story | SP | Status |
|----|------|-------|----|--------|
| T-14 | Port-Migration 8000 → 7995 in allen Files | US-09 | 0.5 | ✅ Done |
| T-15 | Auto-Fallback in `_get_detector()` härten | US-10 | 1 | ✅ Done |
| T-16 | `/health` um `detector`-Feld erweitern, `VisualClient.health_info()` | US-10 | 0.5 | ✅ Done |
| T-17 | Hailo-Detector: robustes `_shutdown_pipeline()` mit Fallback-Pfaden | US-11 | 1 | ✅ Done |
| T-18 | `Anleitung.md` für Controller-Team schreiben | US-12 | 1 | ✅ Done |
| T-19 | `VISUAL_HOST` konfigurierbar (Default 127.0.0.1) | US-13 | 0.5 | ✅ Done |
| T-20 | Pi-Live-Session: Hailo-Stream zum Laufen bringen | US-11 | 3 | ⏳ Open |
| T-21 | Joint-Test mit Audio + Controller-Team | US-13 | 2.5 | ⏳ Open |

### Definition of Ready

- Port-Ranges sind vom Prof verteilt ✓
- Audio-Team hat ihre Endpoints gemeldet (Port 8011 `/speech`) ✓
- COCO-Label-Mapping liegt beim Audio-Team ✓
- Hardware (Pi + Hailo-Kit) ist verfügbar oder ein Fallback ist definiert ✓

### Definition of Done

- Tests grün auf dem Laptop (Fake + Server + Live-E2E mit YOLO) ✓
- Server startet auf dem Pi (Hailo *oder* YOLO-Fallback)
- Controller-Team hat `Anleitung.md` gelesen, kann ohne Rückfragen integrieren
- Joint-End-to-End-Test bestanden: gesprochener Befehl löst Detection aus,
  Koordinaten kommen sinnvoll beim Controller an
- `/health` zeigt den tatsächlichen aktiven Detector, nicht den gewünschten
- Port 7995 konsistent in allen Files

### Offene Punkte / Risiken

- **Hailo-Live-Test auf dem Pi** noch nicht durchgeführt (T-20). Höchstes
  Risiko im Sprint. Geplante Joint-Session: tbd.
- **`app.shutdown()` bei Hailo:** unsicher, ob das so existiert. Fallback
  über `pipeline.set_state(Gst.State.NULL)` ist eingebaut — muss am
  echten Hailo verifiziert werden.
- **Joint-Test mit Audio:** synchroner Termin nötig. Audio kann
  unabhängig getestet werden (POST `/speech`), aber den Loop schließt erst
  der Controller, sobald alle drei Teams parallel laufen.
- **Latenz im Auto-Fallback-Pfad:** wenn Hailo *fast* funktioniert (z.B.
  hängt beim ersten Stream-Versuch), könnte der Fallback erst nach
  Timeout greifen. Im Worst Case Server beim ersten `/track/start` 30s+
  blockiert. Sollte beim Pi-Test geprüft werden.

---

## Sprint 2 — abgeschlossen

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

**Gesamt: 9 Story Points** — alle abgeschlossen.

### Sprint Backlog (final)

| ID | Task | Story | SP | Status |
|----|------|-------|----|--------|
| T-08 | `DetectorProtocol.stream()` + `w`/`h` in `VisionResult` | US-05/08 | 1 | ✅ Done |
| T-09 | `YoloDetector.stream()` umbauen, w/h liefern | US-05/08 | 2 | ✅ Done |
| T-10 | `HailoDetector.stream()` umbauen, w/h liefern | US-05/08 | 2 | ✅ Code Done — Live-Test nach Sprint 3 T-20 verschoben |
| T-11 | `visual.py`: Tracking-API + Sliding-Window-Aggregation | US-06 | 2 | ✅ Done |
| T-12 | `server.py`: FastAPI mit `/track/*` Endpoints | US-07 | 1 | ✅ Done |
| T-13 | `test_visual.py`: Fake- und Server-Tests, `live_e2e_test.py` | US-05/06/07 | 1 | ✅ Done |

### Sprint-2-Retro (kurz)

- ✅ Tests grün auf dem Laptop
- ✅ Controller-Team konnte gegen Server pollen (in Sync-Meeting bestätigt)
- ✅ Alte API entfernt, keine Legacy-Pfade mehr
- ⏳ Hailo-Stream-Live-Test → übernommen in Sprint 3 als T-20
- 💡 Learning: Hardware-abhängige Tasks früher einplanen, nicht ans Sprint-Ende

---

## Sprint 1 — abgeschlossen

**Zeitraum:** KW 17 – KW 18 (21.04.2026 – 27.04.2026)

### Sprint Goal
Funktionierendes `search(object_name) -> dict` mit Hailo auf dem Pi und
YOLO als Laptop-Fallback. Detector-Abstraktion über `DetectorProtocol`,
damit das Visual-Modul ohne Hardware entwickelt werden kann.

### Wichtigste Outcomes

- `DetectorProtocol` etabliert; `HailoDetector`, `YoloDetector`,
  `MockDetector` als Implementierungen
- Einmalige `search()`-Funktion mit Timeout und Stable-Frame-Check
- COCO-Label-Mapping zwischen Audio und Visual abgestimmt: Audio mappt,
  Visual nimmt unverändert (Single Source: `coco.yaml`)
- Sprint-1-Retro: Architektur-Entscheidungen früher mit Controller-Team
  abstimmen → in Sprint 2 umgesetzt
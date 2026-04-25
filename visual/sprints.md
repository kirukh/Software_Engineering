# Team Visual — Sprint README

> Sprint-Länge: **1 Woche** | Hardware: **Raspberry Pi 5 + Hailo-8 AI Kit**
> Zentrale Methode: `search(request: dict) → dict` in `visual.py`

---

## Rückblick auf alle Sprints

| Sprint | Zeitraum | Ziel | Status |
|--------|----------|------|--------|
| Sprint 1 | KW 17 – KW 18 | `search()` mit Hailo + YOLO-Fallback | ✅ Done |

---

## Sprint 1

**Zeitraum:** KW 17 – KW 18 (20.04.2026 – 27.04.2026)

### Sprint Goal
Eine vollständig funktionierende `search()`-Funktion in `visual.py`, die ein
Dict vom Controller entgegennimmt, das Objekt über die Hailo-8 Detection App
identifiziert und ein Ergebnis-Dict (`name`, `found`, `confidence`, `x`, `y`)
zurückliefert. Lokal ohne Hardware kommt `YoloDetector` mit Webcam zum Einsatz.

### Architektur-Entscheidung im Sprint

Ursprünglich war eine REST-API zwischen Controller und Visual angedacht.
Mitten im Sprint haben wir uns dagegen entschieden: beide Module laufen fest
verbaut im selben Prozess — direkter Funktionsaufruf ist einfacher und
schneller. Async-Verhalten (start/poll/cancel) bleibt erhalten, läuft jetzt
über Threads statt HTTP.

### User Stories

| ID | Story | Akzeptanzkriterium | SP |
|----|-------|--------------------|----|
| US-01 | Kamerabild aufnehmen. | Bild wird erfolgreich von der Hardware geladen. | 2 |
| US-02 | Hailo-8 zur Objektidentifikation nutzen. | Liefert `name`, `found`, `confidence`, `x`, `y`. | 5 |
| US-03 | Controller ruft `search(request)` auf, bekommt korrektes Dict. | Funktioniert bei Fund und Nicht-Fund. | 3 |
| US-04 | Lokales Testen ohne Pi. | YoloDetector liefert Ergebnis im selben Format wie HailoDetector. | 2 |

**Gesamt: 12 Story Points**

### Sprint Backlog

| ID | Task | Story | SP | Status |
|----|------|-------|----|--------|
| T-01 | Detection-Interface (`DetectorProtocol`, `VisionResult`) | US-02 | 1 | ✅ Done |
| T-02 | `HailoDetector` implementieren | US-02 | 3 | ✅ Done |
| T-03 | `YoloDetector` als hardware-loser Fallback | US-04 | 2 | ✅ Done |
| T-04 | Kamera-Zugriff (PiCamera2 / Webcam via OpenCV) | US-01 | 2 | ✅ Done |
| T-05 | `search(request) -> dict` (sync + async) | US-03 | 2 | ✅ Done |
| T-06 | End-to-End Test: Controller → `search()` → Dict | US-03 | 1 | ✅ Done |
| T-07 | Tests für `search()` mit Fake-Detector + Live-Test | US-03/04 | 1 | ✅ Done |

### Definition of Ready

- Story ist vom Team verstanden und besprochen
- Akzeptanzkriterien definiert, Story Points geschätzt
- Abhängigkeiten zum Controller-Team geklärt
- Pi mit Hailo-8 verfügbar, Detection App identifiziert
- Detection-Interface spezifiziert vor Implementierung

### Definition of Done

- Code auf dem Pi (mit Hailo) lauffähig
- YoloDetector-Tests laufen lokal ohne Hardware
- `search()` gibt korrektes Dict-Format zurück
- End-to-End Test mit Controller erfolgreich
- `HailoDetector` und `YoloDetector` implementieren `DetectorProtocol`
- Code reviewed, in `main` gemergt, Doku aktualisiert
- Keine offenen Bugs

---

### Sprint-Ergebnis & Retro

**Erreichte Story Points:** 12 / 12

**Was lief gut?**
- Klares Detector-Interface — Wechsel Hailo ↔ YOLO ist trivial.
- Hardware-loses Entwickeln mit YOLO + Webcam war für das ganze Team produktiv.
- Live-Test mit echter Webcam + Smartphone bestätigt End-to-End-Funktionalität.

**Was lief nicht gut?**
- Anfangs auf REST-API gesetzt — mitten im Sprint zurückgerudert, da nicht nötig.

**Was verbessern wir im nächsten Sprint?**
- Architektur-Entscheidungen früher mit Controller-Team abstimmen.

**Velocity:** 12 SP erreicht / 12 SP geplant
**Fazit für Sprint 2:** Schätzungen waren realistisch — als Baseline nutzbar.
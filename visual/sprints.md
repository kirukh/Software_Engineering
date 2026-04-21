# Team Visual – Sprint README

> Dieses Dokument wird nach jedem Sprint aktualisiert.  
> Sprint-Länge: **1 Woche** | Hardware: **Raspberry Pi 5 + Hailo-8 AI Kit**  
> Zentrale Methode: `search(object_name: str) → dict` in `visual.py`

---

## Rückblick auf alle Sprints

| Sprint | Zeitraum | Ziel | Status |
|--------|----------|------|--------|
| Sprint 1 | KW 17 – KW 18 | search()-Funktion mit Mock-Controller + Hailo-Workaround |  In Progress |

---

## Sprint 1

**Zeitraum:** KW 17 – KW 18 (20.04.2026 – 27.04.2026)

### Sprint Goal
> Eine vollständig funktionierende `search()`-Funktion in `visual.py`, die eine Suchanfrage vom Controller entgegennimmt, das gesuchte Objekt über die Hailo-8 Detection App auf dem Raspberry Pi identifiziert und das korrekte Ergebnis-Dictionary zurückliefert.  
> Lokal wird ein `MockDetector` eingesetzt, damit das Team ohne Hardware entwickeln und testen kann.

---

### User Stories

| ID | Story | Akzeptanzkriterium | SP |
|----|-------|--------------------|----|
| US-01 | Als Visual-Modul möchte ich ein aktuelles Kamerabild über PiCamera2 aufnehmen. | Bild wird erfolgreich von der Hardware geladen. | 2 |
| US-02 | Als Visual-Modul möchte ich die Hailo-8 Detection App nutzen, um ein Objekt im Bild zu identifizieren. | Detection App liefert `name`, `found` (bool), `confidence` (float 0–1). | 5 |
| US-03 | Als Mock-Controller möchte ich `search(object_name)` aufrufen und ein korrektes Dict erhalten. | `search()` gibt Dict korrekt zurück – bei Fund und Nicht-Fund. Testbar mit Mock-Controller. | 3 |
| US-04 | Als Entwickler möchte ich `search()` lokal ohne Raspberry Pi testen können. | `MockDetector` liefert deterministisches Test-Dict im selben Format wie `HailoDetector`. | 2 |

**Gesamt: 12 Story Points**

---

### Sprint Backlog

| ID | Task | Story | SP | Status |
|----|------|-------|----|--------|
| T-01 | Detection-Interface definieren (abstrakte Klasse / Protokoll) | US-02 | 1 |  To Do |
| T-02 | `HailoDetector` implementieren (Raspberry Pi, vorhandene Detection App) | US-02 | 3 |  To Do |
| T-03 | `MockDetector` implementieren (lokal, deterministisch, gleiches Interface) | US-04 | 2 |  To Do |
| T-04 | Kamera-Zugriff auf Raspberry Pi (PiCamera2) | US-01 | 2 |  To Do |
| T-05 | `search()`-Funktion implementieren (nimmt String, gibt Dict zurück) | US-03 | 2 |  To Do |
| T-06 | End-to-End Test: Mock-Controller → `search()` → Dict | US-03 | 1 |  To Do |
| T-07 | Unit Tests für `search()` mit `MockDetector` schreiben | US-03/04 | 1 |  To Do |


---

### Definition of Ready (DoR)

Eine User Story ist bereit für den Sprint, wenn:

- Die Story ist vom gesamten Team verstanden und besprochen
- Klare und vollständige Akzeptanzkriterien sind definiert
- Story Points sind geschätzt und vom Team akzeptiert
- Abhängigkeiten zum Controller-Team (Mock-Controller Interface) sind geklärt
- Raspberry Pi mit Hailo-8 AI Kit ist verfügbar
- Die vorhandene Hailo Detection App ist identifiziert und der Aufruf ist bekannt
- Das Detection-Interface ist spezifiziert bevor die Implementierung startet
- Die Schnittstelle zum Controller ist dokumentiert und abgestimmt

---

### Definition of Done (DoD)

Eine User Story gilt als abgeschlossen, wenn:

- Code ist implementiert und auf dem Raspberry Pi (mit Hailo) lauffähig
- `MockDetector`-Tests laufen lokal durch (unabhängig von Hardware)
- `search()` gibt das korrekte Dictionary-Format zurück (`name`, `found`, `confidence`)
- End-to-End Test mit Mock-Controller erfolgreich: Eingabe → `search()` → Dict
- `HailoDetector` und `MockDetector` implementieren dasselbe Interface
- Akzeptanzkriterien der Story sind vollständig erfüllt
- Code wurde reviewed und in den `main`-Branch gemergt
- README / Dokumentation wurde aktualisiert
- Kein bekannter Bug ist offen (oder bewusst als Tech Debt dokumentiert)

---

### Sprint Ergebnis & Retro

*(Nach Sprint-Ende ausfüllen)*

**Erreichte Story Points:** __ / 12

**Was lief gut?**
-

**Was lief nicht gut?**
-

**Was verbessern wir im nächsten Sprint?**
-

**Velocity:** __ SP erreicht / 12 SP geplant  
**Fazit für Schätzungen in Sprint 2:**
# Visual Team - README

## Übersicht
Das Visual-Team ist verantwortlich für Objekterkennung mittels Kameraeingabe und KI-gestützter Bildanalyse.

## Team-Aufgaben

- **Eingabe**: Objektspezifikation vom Audio-Team über Controller empfangen
- **Bilderfassung**: Bilder von der Kamera-Hardware erfassen
- **Objekterkennung**: KI-gestützte Analyse durchführen, um Zielobjekte zu identifizieren
- **Ausgabe**: Tuple mit Erkennungsstatus und Konfidenz an Controller zurückgeben

## Workflow

**Methode**: `search()` in `visual.py`

**Prozess**:
1. Controller empfängt Eingabe vom Audio-Team
2. Controller ruft `search()`-Funktion mit Objektparameter auf
3. Visual-Team startet Kamerasuche
4. Bilder mittels AI-Detection-Modul analysieren
5. Dictionary erstellen mit Objektname, gefunden und Konfidenz
6. Dictionary mit Objektname, nicht gefunden und Konfidenz wenn nicht gefunden

## Funktionale Anforderungen

| ID | Anforderung |
|---|---|
| FR-01 | Objektsuchanfragen als Eingabeparameter vom Controller akzeptieren |
| FR-02 | Bilder von der Kamera-Hardware erfassen |
| FR-03 | KI-gestützte Bildanalyse zur Objektidentifikation durchführen |
| FR-04 | Dictionary mit Objektname, Erkennungsstatus (true/false) und Konfidenzwert zurückgeben |

## Cross-Team-Integration

| ID | Anforderung |
|---|---|
| ITF-01 | Objektsuchanfragen vom Audio-Team über Controller empfangen |
| ITF-02 | Erkennungsergebnis-Dict (name, boolean, confidence) an Controller zurückgeben |

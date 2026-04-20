"""
MockDetector — lokaler Ersatz für HailoDetector (T-03, US-04).

Deterministisch und hardware-unabhängig. Liefert dasselbe Interface wie
HailoDetector, damit search() lokal vollständig getestet werden kann.

Verhalten (konfigurierbar über Konstruktor):
  - found_objects: set von Objektnamen, die als "gefunden" gelten
  - default_confidence: Konfidenz die zurückgegeben wird wenn found=True
"""
from __future__ import annotations

from vision_interface import DetectorProtocol, VisionResult


class MockDetector:
    """
    Deterministischer Test-Detektor ohne Hardware (US-04).

    Implementiert DetectorProtocol — austauschbar mit HailoDetector.

    Beispiel:
        detector = MockDetector(found_objects={"smartphone", "cup"})
        result = detector.detect("smartphone")
        # → VisionResult(name='smartphone', found=True, confidence=0.91)
    """

    def __init__(
        self,
        found_objects: set[str] | None = None,
        default_confidence: float = 0.91,
    ) -> None:
        """
        Args:
            found_objects:      Menge der Objekte, die als erkannt gelten.
                                None oder leeres Set → immer found=False.
            default_confidence: Konfidenz für erkannte Objekte (0.0–1.0).
        """
        self._found_objects: set[str] = found_objects or set()
        self._default_confidence = default_confidence

    def detect(self, object_name: str) -> VisionResult:
        """Deterministisch: gibt found=True zurück wenn object_name in found_objects."""
        normalized = object_name.strip().lower()
        if normalized in {o.lower() for o in self._found_objects}:
            return VisionResult(
                name=object_name,
                found=True,
                confidence=self._default_confidence,
            )
        return VisionResult(name=object_name, found=False, confidence=0.0)


# Sicherstellen dass MockDetector das Protokoll erfüllt
assert isinstance(MockDetector(), DetectorProtocol), (
    "MockDetector implementiert DetectorProtocol nicht korrekt"
)

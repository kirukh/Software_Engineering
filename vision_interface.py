"""
Shared types and detector protocol for Team Visual (Sprint 1).

DetectorProtocol: abstrakte Schnittstelle, die HailoDetector und MockDetector
                  implementieren müssen.
VisionResult:     einheitliches Dict-ähnliches Ergebnis-Dataclass.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Ergebnis-Format (US-02, US-03)
# ---------------------------------------------------------------------------

@dataclass
class VisionResult:
    """
    Rückgabeformat von search() und detect().

    name:       gesuchtes Objekt (wie vom Controller übergeben)
    found:      True wenn Objekt stabil erkannt, False sonst
    confidence: Konfidenz des letzten besten Frames (0.0 wenn not found)
    """
    name: str
    found: bool
    confidence: float

    def to_dict(self) -> dict:
        return {"name": self.name, "found": self.found, "confidence": self.confidence}


# ---------------------------------------------------------------------------
# Detektor-Protokoll / Interface (T-01)
# ---------------------------------------------------------------------------

@runtime_checkable
class DetectorProtocol(Protocol):
    """
    Abstrakte Schnittstelle für alle Detektoren.
    Implementiert von: HailoDetector, MockDetector.
    """

    def detect(self, object_name: str) -> VisionResult:
        """
        Sucht nach object_name im aktuellen Kamerastream.

        Gibt ein VisionResult zurück:
          - found=True  + confidence wenn stabil erkannt
          - found=False + confidence=0.0 wenn nicht erkannt
        """
        ...

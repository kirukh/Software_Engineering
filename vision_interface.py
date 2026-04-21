"""
Shared types and detector protocol for Team Visual (Sprint 1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class VisionResult:
    name: str
    found: bool
    confidence: float
    x: float | None = None
    y: float | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "found": self.found,
            "confidence": self.confidence,
            "x": self.x,
            "y": self.y,
        }


@runtime_checkable
class DetectorProtocol(Protocol):
    def detect(self, object_name: str) -> VisionResult:
        ...
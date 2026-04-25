"""
test_visual.py — Tests für die Visual-Schnittstelle.

    python test_visual.py           # Fake-Tests, ohne Hardware
    python test_visual.py --live    # zusätzlich: echter Webcam-Test mit Smartphone
"""
from __future__ import annotations

import sys
import time

import visual
from vision_interface import VisionResult


# ------------------------------------------------------------------ Fakes

class _FakeFound:
    def detect(self, name): return VisionResult(name, True, 0.92, 0.5, 0.5)


class _FakeNotFound:
    def detect(self, name): return VisionResult(name, False, 0.0)


class _SlowFake:
    """Simuliert langsame Detection — wichtig für den Cancel-Test."""
    def detect(self, name):
        time.sleep(2.0)
        return VisionResult(name, True, 0.8, 0.3, 0.7)


def trennlinie(titel: str) -> None:
    print(f"\n{'='*50}\n  {titel}\n{'='*50}")


# ------------------------------------------------------------------ Fake Tests

def run_fake_tests() -> None:
    trennlinie("Test 1: Sync search() — gefunden")
    visual.set_detector(_FakeFound())
    result = visual.search({"name": "smartphone"})
    print(f"  {result}")
    assert result == {"name": "smartphone", "found": True, "confidence": 0.92, "x": 0.5, "y": 0.5}
    print("  ✓ Dict-Format korrekt")

    trennlinie("Test 2: Sync search() — nicht gefunden")
    visual.set_detector(_FakeNotFound())
    result = visual.search({"name": "laptop"})
    print(f"  {result}")
    assert result["found"] is False and result["x"] is None and result["y"] is None
    print("  ✓ Not-Found-Fall korrekt")

    trennlinie("Test 3: Ungültige Anfragen")
    for bad in [{}, {"falsch": "x"}, {"name": ""}, {"name": "   "}, "kein dict"]:
        try:
            visual.search(bad)
            raise AssertionError(f"Erwartet ValueError für {bad!r}")
        except ValueError as e:
            print(f"  ✓ {bad!r} → {e}")

    trennlinie("Test 4: Async start_search() + get_result()")
    visual.set_detector(_FakeFound())
    job = visual.start_search({"name": "cup"})
    print(f"  Gestartet: {job}")
    time.sleep(0.2)
    result = visual.get_result(job["job_id"])
    print(f"  {result}")
    assert result["status"] == "done" and result["found"] is True
    print("  ✓ Async-Flow funktioniert")

    trennlinie("Test 5: Cancel eines laufenden Jobs")
    visual.set_detector(_SlowFake())
    job = visual.start_search({"name": "bottle"})
    job_id = job["job_id"]
    time.sleep(0.1)
    assert visual.get_result(job_id)["status"] == "running"
    print(f"  Cancel: {visual.cancel(job_id)}")
    assert visual.get_result(job_id)["status"] == "cancelled"
    print("  ✓ Cancel funktioniert")

    trennlinie("Test 6: Unbekannte job_id")
    result = visual.get_result("gibt-es-nicht")
    print(f"  {result}")
    assert result["status"] == "unknown"
    print("  ✓ Unknown-Fall korrekt")


# ------------------------------------------------------------------ Live Test

def run_live_test() -> None:
    """Echter End-to-End-Test mit Webcam + YOLO."""
    import os
    os.environ["VISUAL_DETECTOR"] = "yolo"
    visual.set_detector(None)  # vorherige Fakes wegwerfen

    trennlinie("LIVE-Test: Webcam + echtes Smartphone")
    print("  ▶  Halte dein Smartphone gut sichtbar in die Kamera (Timeout 30s).")
    input("  ⏎  Enter zum Starten ...")

    start = time.monotonic()
    result = visual.search({"name": "smartphone"})
    print(f"\n  Ergebnis: {result}")
    print(f"  Dauer: {time.monotonic() - start:.1f}s")

    assert result["name"] == "smartphone"
    assert result["found"] is True, (
        "Smartphone NICHT erkannt — Licht / Konfidenz-Schwelle "
        "(VISION_CONFIDENCE_MIN) / VISION_STABLE_FRAMES prüfen."
    )
    assert result["confidence"] >= 0.5
    assert 0.0 <= result["x"] <= 1.0 and 0.0 <= result["y"] <= 1.0
    print(f"  ✓ Erkannt mit Konfidenz {result['confidence']:.2f} bei "
          f"x={result['x']:.2f}, y={result['y']:.2f}")


# ------------------------------------------------------------------ Main

if __name__ == "__main__":
    run_fake_tests()

    if "--live" in sys.argv:
        run_live_test()
        trennlinie("Alle Tests bestanden ✓ (inkl. Live-Test)")
    else:
        trennlinie("Alle Fake-Tests bestanden ✓")
        print("\n  Tipp: Live-Test mit Webcam → python test_visual.py --live")
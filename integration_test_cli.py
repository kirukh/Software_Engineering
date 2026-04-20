"""
integration_test_cli.py — End-to-End Test (T-06).

Simuliert den Mock-Controller-Aufruf: Controller → search() → Dict.
Kein Mikrofon, keine Hailo-Kamera nötig.

Verwendung:
    VISUAL_USE_MOCK=1 python integration_test_cli.py
"""
from __future__ import annotations

import json

from mock_detector import MockDetector
from visual import search, set_detector


def run() -> None:
    # MockDetector mit bekannten Objekten injizieren
    set_detector(MockDetector(found_objects={"smartphone", "bottle"}, default_confidence=0.92))

    print("=== Integration Test: Mock-Controller → search() → Dict ===\n")

    test_cases = [
        ("smartphone", True),
        ("bottle",     True),
        ("keys",       False),
        ("cup",        False),
    ]

    all_passed = True
    for object_name, expected_found in test_cases:
        result = search(object_name)
        passed = result["found"] == expected_found
        status = "✓ PASS" if passed else "✗ FAIL"
        if not passed:
            all_passed = False
        print(f"{status}  search({object_name!r})")
        print(f"       → {json.dumps(result)}")
        print()

    print("=== Ergebnis:", "ALLE TESTS BESTANDEN ✓" if all_passed else "FEHLER ✗", "===")


if __name__ == "__main__":
    run()

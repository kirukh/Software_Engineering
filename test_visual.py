"""
Unit Tests für search() mit MockDetector (T-07, US-03, US-04).

Laufen lokal ohne Raspberry Pi / Hailo-Hardware.

Ausführen:
    python -m pytest test_visual.py -v
    # oder ohne pytest:
    python test_visual.py
"""
from __future__ import annotations

import sys
import unittest

from mock_detector import MockDetector
from vision_interface import DetectorProtocol, VisionResult
from visual import search, set_detector


class TestMockDetector(unittest.TestCase):
    """T-03 / US-04: MockDetector liefert deterministisches Dict im richtigen Format."""

    def test_found_object_returns_correct_result(self):
        detector = MockDetector(found_objects={"smartphone"}, default_confidence=0.91)
        result = detector.detect("smartphone")
        self.assertIsInstance(result, VisionResult)
        self.assertTrue(result.found)
        self.assertEqual(result.name, "smartphone")
        self.assertAlmostEqual(result.confidence, 0.91)

    def test_not_found_object_returns_false(self):
        detector = MockDetector(found_objects={"smartphone"})
        result = detector.detect("cup")
        self.assertFalse(result.found)
        self.assertEqual(result.confidence, 0.0)

    def test_empty_found_set_always_returns_false(self):
        detector = MockDetector()
        result = detector.detect("smartphone")
        self.assertFalse(result.found)

    def test_case_insensitive_matching(self):
        detector = MockDetector(found_objects={"Smartphone"})
        result = detector.detect("smartphone")
        self.assertTrue(result.found)

    def test_implements_protocol(self):
        """MockDetector und HailoDetector müssen dasselbe Interface haben (DoD)."""
        self.assertIsInstance(MockDetector(), DetectorProtocol)


class TestSearchFunction(unittest.TestCase):
    """T-05 / T-06 / US-03: search() gibt korrektes Dict-Format zurück."""

    def setUp(self):
        # Dependency Injection: MockDetector direkt setzen (unabhängig von Env-Vars)
        set_detector(MockDetector(found_objects={"smartphone"}, default_confidence=0.85))

    def test_search_found_returns_correct_dict(self):
        result = search("smartphone")
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertIn("found", result)
        self.assertIn("confidence", result)
        self.assertTrue(result["found"])
        self.assertEqual(result["name"], "smartphone")
        self.assertAlmostEqual(result["confidence"], 0.85)

    def test_search_not_found_returns_correct_dict(self):
        result = search("cup")
        self.assertIsInstance(result, dict)
        self.assertFalse(result["found"])
        self.assertEqual(result["name"], "cup")
        self.assertEqual(result["confidence"], 0.0)

    def test_search_returns_exact_three_fields(self):
        """Dict hat genau die Felder name, found, confidence — nicht mehr."""
        result = search("smartphone")
        self.assertEqual(set(result.keys()), {"name", "found", "confidence"})

    def test_search_found_is_bool(self):
        result = search("smartphone")
        self.assertIsInstance(result["found"], bool)

    def test_search_confidence_is_float(self):
        result = search("smartphone")
        self.assertIsInstance(result["confidence"], float)

    def test_search_name_matches_input(self):
        result = search("laptop")
        self.assertEqual(result["name"], "laptop")

    def test_search_strips_whitespace(self):
        result = search("  smartphone  ")
        self.assertEqual(result["name"], "smartphone")

    def test_search_raises_on_empty_string(self):
        with self.assertRaises(ValueError):
            search("")

    def test_search_raises_on_non_string(self):
        with self.assertRaises(ValueError):
            search(None)  # type: ignore[arg-type]


class TestEndToEnd(unittest.TestCase):
    """
    T-06: End-to-End Test — Mock-Controller → search() → Dict.

    Simuliert den kompletten Aufruf wie er vom Controller kommt.
    """

    def setUp(self):
        set_detector(MockDetector(found_objects={"smartphone", "bottle"}))

    def test_mock_controller_found(self):
        """Controller ruft search() auf — Objekt gefunden."""
        # Wie der Controller es aufrufen würde:
        result = search("smartphone")
        self.assertTrue(result["found"])
        self.assertGreater(result["confidence"], 0.0)

    def test_mock_controller_not_found(self):
        """Controller ruft search() auf — Objekt nicht gefunden."""
        result = search("keys")
        self.assertFalse(result["found"])
        self.assertEqual(result["confidence"], 0.0)

    def test_multiple_searches_independent(self):
        """Mehrere Aufrufe von search() sind voneinander unabhängig."""
        r1 = search("smartphone")
        r2 = search("keys")
        r3 = search("bottle")
        self.assertTrue(r1["found"])
        self.assertFalse(r2["found"])
        self.assertTrue(r3["found"])


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestMockDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestSearchFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEnd))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

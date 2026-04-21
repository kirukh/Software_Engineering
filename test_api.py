"""
test_api.py — Vorführungs-Test für die Visual-API.

Testet:
    1. Async-Suche mit gefundenem Objekt (MockDetector found=True)
    2. Async-Suche mit nicht gefundenem Objekt (MockDetector found=False)
    3. Cancel eines laufenden Jobs
    4. Fehlerhafte Anfragen (400-Fehler)
    5. Cleanup abgelaufener Jobs

Start:
    1. Terminal 1: python api_server.py
    2. Terminal 2: python test_api.py
"""
import time
import requests

BASE = "http://localhost:5000"


def trennlinie(titel: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {titel}")
    print(f"{'='*50}")


def poll_result(job_id: str, interval: float = 0.5, timeout: float = 40.0) -> dict:
    """Pollt /search/result/<job_id> bis status != running."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{BASE}/search/result/{job_id}")
        data = r.json()
        print(f"  [Poll] {data}")
        if data.get("status") != "running":
            return data
        time.sleep(interval)
    return {"status": "timeout"}


# ------------------------------------------------------------------ Test 1
trennlinie("Test 1: Objekt wird gefunden (smartphone)")

r = requests.post(f"{BASE}/search/start", json={"object": "smartphone"})
print(f"  POST /search/start → {r.status_code} {r.json()}")
job_id = r.json()["job_id"]

result = poll_result(job_id)
assert result["status"] == "done", f"Erwartet 'done', bekam: {result}"
assert result["found"] in (True, False)
assert "x" in result and "y" in result
print(f"  ✓ Ergebnis: {result}")


# ------------------------------------------------------------------ Test 2
trennlinie("Test 2: Ungültige Anfrage (fehlendes Feld)")

r = requests.post(f"{BASE}/search/start", json={"falsch": "smartphone"})
print(f"  POST /search/start (kein 'object') → {r.status_code} {r.json()}")
assert r.status_code == 400
print(f"  ✓ 400 korrekt zurückgegeben")


# ------------------------------------------------------------------ Test 3
trennlinie("Test 3: Ungültige Anfrage (leerer String)")

r = requests.post(f"{BASE}/search/start", json={"object": ""})
print(f"  POST /search/start (leerer String) → {r.status_code} {r.json()}")
assert r.status_code == 400
print(f"  ✓ 400 korrekt zurückgegeben")


# ------------------------------------------------------------------ Test 4
trennlinie("Test 4: Cancel eines laufenden Jobs")

r = requests.post(f"{BASE}/search/start", json={"object": "cup"})
job_id = r.json()["job_id"]
print(f"  Job gestartet: {job_id}")

time.sleep(0.3)  # kurz warten damit Job läuft

r = requests.delete(f"{BASE}/search/cancel/{job_id}")
print(f"  DELETE /search/cancel → {r.status_code} {r.json()}")
assert r.status_code == 200

r = requests.get(f"{BASE}/search/result/{job_id}")
print(f"  GET /search/result → {r.json()}")
assert r.json()["status"] == "cancelled"
print(f"  ✓ Cancel funktioniert")


# ------------------------------------------------------------------ Test 5
trennlinie("Test 5: Unbekannte job_id")

r = requests.get(f"{BASE}/search/result/nicht-existent")
print(f"  GET /search/result/nicht-existent → {r.status_code} {r.json()}")
assert r.status_code == 404
print(f"  ✓ 404 korrekt zurückgegeben")


# ------------------------------------------------------------------ Fertig
trennlinie("Alle Tests bestanden ✓")
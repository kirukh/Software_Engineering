"""
api_server.py — Async REST-API für Team Visual.

Endpunkte:
    POST   /search/start           → startet Suche, gibt job_id zurück
    GET    /search/result/<job_id> → gibt Status/Ergebnis zurück
    DELETE /search/cancel/<job_id> → bricht laufende Suche ab
"""
from __future__ import annotations

import threading
import time
import uuid

from flask import Flask, jsonify, request

from visual import search

app = Flask(__name__)

_jobs: dict = {}
_jobs_lock = threading.Lock()
JOB_MAX_AGE_SECONDS = 60


def _cleanup_jobs() -> None:
    while True:
        time.sleep(30)
        now = time.monotonic()
        with _jobs_lock:
            to_delete = [
                job_id for job_id, job in _jobs.items()
                if job["status"] != "running"
                and now - job["finished_at"] > JOB_MAX_AGE_SECONDS
            ]
            for job_id in to_delete:
                del _jobs[job_id]
                print(f"[Cleanup] Job {job_id} gelöscht")


def _run_search(job_id: str, object_name: str) -> None:
    try:
        result = search(object_name)
        with _jobs_lock:
            if _jobs[job_id]["status"] == "running":
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["result"] = result
                _jobs[job_id]["finished_at"] = time.monotonic()
    except Exception as e:
        with _jobs_lock:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["result"] = str(e)
            _jobs[job_id]["finished_at"] = time.monotonic()


@app.route("/search/start", methods=["POST"])
def search_start():
    data = request.get_json()

    if not data or "object" not in data:
        return jsonify({"error": "Feld 'object' fehlt im Request-Body"}), 400

    object_name = data["object"]
    if not isinstance(object_name, str) or not object_name.strip():
        return jsonify({"error": "'object' muss ein nicht-leerer String sein"}), 400

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "running", "result": None, "finished_at": None}

    thread = threading.Thread(target=_run_search, args=(job_id, object_name), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id}), 202


@app.route("/search/result/<job_id>", methods=["GET"])
def search_result(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)

    if job is None:
        return jsonify({"error": "job_id nicht gefunden"}), 404

    if job["status"] == "running":
        return jsonify({"status": "running"}), 200

    if job["status"] == "error":
        return jsonify({"status": "error", "message": job["result"]}), 500

    if job["status"] == "cancelled":
        return jsonify({"status": "cancelled"}), 200

    return jsonify({"status": "done", **job["result"]}), 200


@app.route("/search/cancel/<job_id>", methods=["DELETE"])
def search_cancel(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)

    if job is None:
        return jsonify({"error": "job_id nicht gefunden"}), 404

    with _jobs_lock:
        if _jobs[job_id]["status"] == "running":
            _jobs[job_id]["status"] = "cancelled"
            _jobs[job_id]["finished_at"] = time.monotonic()

    return jsonify({"cancelled": job_id}), 200


if __name__ == "__main__":
    cleanup_thread = threading.Thread(target=_cleanup_jobs, daemon=True)
    cleanup_thread.start()
    app.run(host="0.0.0.0", port=5000)
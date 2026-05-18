**Visual module — full change summary**

This is everything that changed in the Visual module since Sprint 1, in one place. Use it to plan your migration.

---

## TL;DR

The old in-process Python API (`from visual import search, ...`) is gone. The Visual module is now a standalone **HTTP server** (FastAPI on `127.0.0.1:7995`) that you talk to over the network. We ship a Python client (`visual_client.py`) so you don't have to write raw HTTP calls.

The detection model also changed: instead of one-shot `search()` calls, the server runs **continuous tracking** in the background, and you poll the latest aggregated result.

> **Port:** Visual sits in the 7991–8000 range (assignment from Prof. Jehle). Default port is **7995**.
> **Detector fallback:** if Hailo isn't available at runtime, the server silently falls back to YOLO so the rollout doesn't break. `GET /health` shows which one is active.

---

## What was removed

- `from visual import search` — **gone**
- `from visual import start_search, get_result, cancel` — **gone**
- The `__init__.py` package interface — **gone**
- The `job_id` concept (UUID returned by `start_search`, polled with `get_result(job_id)`) — **gone**
- `cancel(job_id)` — **replaced by** `stop()` (no job IDs needed anymore)
- `VISION_STABLE_FRAMES` and `VISION_TIMEOUT` env variables — **gone** (no more one-shot detection with timeout)

## What is new

- **HTTP server** on `127.0.0.1:7995` (FastAPI), started via `python server.py`
- **Four endpoints**: `POST /track/start`, `GET /track/latest`, `POST /track/stop`, `GET /health`
- **Python client** `visual_client.py` we ship with the repo
- **Bounding-box size** in the result: `w` and `h`, in addition to `x`, `y` (all normalized 0–1)
- **Continuous tracking** instead of one-shot detection — the detector runs in the background until you stop it
- **Sliding window** of the last 8 frames smooths the output (default: 5 of 8 frames must match for `found=true`)
- **Auto Hailo→YOLO fallback** — when `VISUAL_DETECTOR` is not set, the server tries Hailo first and falls back to YOLO on any error. `GET /health` returns `{"detector": "hailo"|"yolo"|"none"}` so you can verify which one's active.
- **Configurable bind address** — `VISUAL_HOST` env variable, default `127.0.0.1`. Set to `0.0.0.0` for network access.

## Behavioral changes

1. **No more one-shot search.** Previously `search({"name": "smartphone"})` blocked until the object was found or timed out. Now you call `start()`, then poll `latest()` in your main loop, then call `stop()` when done.
2. **Result format changed.** Old: `{name, found, confidence, x, y}`. New: same fields plus `w`, `h`, plus a `status` field (`"running"` / `"idle"`).
3. **`name` must be a valid COCO label** (e.g. `"cell phone"`, `"person"`, `"bottle"`). The previous version internally mapped colloquial terms (`"smartphone"`, `"handy"`) to COCO labels. **That mapping is gone** — the audio team handles label translation now.
4. **The server must be running** when you call it. Either start it manually (`python server.py`) or have your controller process spawn it. There is no in-process API anymore.
5. **Port changed from 8000 to 7995** — make sure your client uses the new default (or pass `base_url="http://127.0.0.1:7995"` explicitly).

## Old code (delete this)

```python
from visual import search, start_search, get_result, cancel

# Old one-shot blocking call:
result = search({"name": "smartphone"})
if result["found"]:
    laser.point_to(result["x"], result["y"])

# Or old async pattern:
job = start_search({"name": "smartphone"})
while True:
    r = get_result(job["job_id"])
    if r["status"] == "done":
        break
    time.sleep(0.1)
cancel(job["job_id"])
```

## New code (use this)

```python
from visual_client import VisualClient
import time

with VisualClient() as visual:                    # default: http://127.0.0.1:7995
    visual.start("cell phone")                    # COCO label from audio team
    while controller_running:
        r = visual.latest()
        if r["status"] == "running" and r["found"]:
            laser.point_to(r["x"], r["y"])        # also r["w"], r["h"] for size
        else:
            laser.idle()
        time.sleep(0.1)
    # stop() is called automatically by the context manager
```

## Response format reference

```python
# Tracking off:
{"status": "idle"}

# Tracking running, nothing detected in current window:
{"status": "running", "name": "cell phone", "found": false,
 "confidence": 0.0, "x": null, "y": null, "w": null, "h": null}

# Tracking running, object detected:
{"status": "running", "name": "cell phone", "found": true,
 "confidence": 0.87, "x": 0.51, "y": 0.48, "w": 0.18, "h": 0.32}

# Health (new):
{"status": "ok", "detector": "hailo"}   # or "yolo" or "none"
```

All coordinates are normalized to 0.0–1.0 (image fraction, not pixels).

## Polling rate

100ms is a good default. The sliding window aggregates the last 8 frames, so a new aggregated value comes in roughly every 250ms (Hailo) or 500ms (YOLO on a laptop). Polling faster doesn't hurt (it's idempotent and cheap), but won't give you fresher data.

## Heads-up about your old `interface.py` wrapper

In the old setup you had a FastAPI wrapper (`/search/{item_name}`, `/cancel`) that called our Python functions internally. **Two things in there are now obsolete:**

- `CONFIDENCE_THRESHOLD = 0.60` — confidence filtering now happens inside Visual (per-frame minimum + sliding-window vote). You don't need a second threshold on your side.
- `TIMEOUT = 40 * 0.5s = 20s` — there's no one-shot detection anymore. Tracking runs until you call `stop()`. If you want a max-search duration, build it as a counter in your polling loop.

**Open question:** do you still want to keep your own FastAPI wrapper as a layer (calling `VisualClient` internally), or call `VisualClient` directly from your main controller logic? Both work — the choice depends on your internal architecture, not ours. Let us know if you want to discuss.

## Why we changed it

The "sustained fire" requirement for the laser came in after Sprint 1. The laser needs continuous coordinate updates, not a single detection result. We considered:

- Subprocess + IPC (pipe/socket) — rejected, hard to debug
- Server-Sent Events / WebSocket — rejected, non-uniform with how other teams communicate
- HTTP polling — chosen, uniform with other teams, easy to inspect with `curl`

## What's still open on our side

- The Hailo path is code-complete but **not yet live-tested on the Pi** (Sprint 3 task T-20). We'll go through that together at the next joint Pi session.
- A central config file (instead of env variables) is on the Sprint 4 backlog.
- A video-stream endpoint (`GET /stream`) is in discussion for Sprint 4.

## Testing it locally without the Pi

If you want to verify your client code against a real running server before the Pi session:

```bash
VISUAL_DETECTOR=yolo python server.py        # uses your laptop webcam
```

Then point your code at `http://127.0.0.1:7995` and try with COCO labels like `"person"` (most reliable) or `"cell phone"`.

## Repo + docs

- `Anleitung.md` — **start here**, step-by-step guide for the controller team
- `README.md` — full HTTP-API reference and config
- `sprints.md` — sprint history with architecture decisions
- `visual_client.py` — ready-to-use Python client with docstrings
- `live_e2e_test.py` — working end-to-end example you can read

Ping me if anything is unclear — happy to walk through it on a call.
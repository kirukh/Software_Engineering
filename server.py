"""HTTP-Server für die Kommunikation mit dem Controller.

FastAPI auf 127.0.0.1:7995 (Default). Endpoints:
    POST   /track/start    Body: {"name": "cell phone"}
    GET    /track/latest   aggregiertes Window-Ergebnis
    POST   /track/stop     Tracking beenden
    GET    /health         Server-Check (inkl. aktiver Detector)

Port 7995 liegt in der Visual-Range 7991–8000 (Festlegung Prof. Jehle).

Konfiguration über Env-Variablen:
    VISUAL_HOST     Default 127.0.0.1 — auf 0.0.0.0 setzen, wenn andere
                    Geräte zugreifen können sollen
    VISUAL_PORT     Default 7995
    VISUAL_DETECTOR Default leer (auto: Hailo > YOLO).
                    'hailo' oder 'yolo' erzwingt einen Detector.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

import visual


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Detector beim Server-Start vorladen, damit /health erst antwortet wenn
    # alles bereit ist und der erste /track/start nicht in einen Timeout läuft.
    print("[server] Detector wird vorgeladen...")
    try:
        visual.prewarm()
        print(f"[server] Bereit. Aktiver Detector: {visual.active_detector()}")
    except Exception as e:
        # Prewarm-Fehler nicht den Server-Start abbrechen lassen — das wäre
        # schlecht im Rollout. Stattdessen loggen, der erste /track/start
        # liefert dann den Fehler.
        print(f"[server] Prewarm fehlgeschlagen: {e}")
    yield
    visual.stop_tracking()


app = FastAPI(
    title="visual_api",
    description="Tracking-API für das Visual-Modul",
    version="0.3.0",
    lifespan=lifespan,
)


# ------------------------------------------------------------------ Schemas

class TrackStartReq(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name darf nicht leer sein")
        return v.strip()


class TrackStartRes(BaseModel):
    status: str
    name: str


class TrackLatestRes(BaseModel):
    status: str  # 'idle' | 'running'
    name: str | None = None
    found: bool | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    x: float | None = Field(default=None, ge=0.0, le=1.0)
    y: float | None = Field(default=None, ge=0.0, le=1.0)
    w: float | None = Field(default=None, ge=0.0, le=1.0)
    h: float | None = Field(default=None, ge=0.0, le=1.0)


class TrackStopRes(BaseModel):
    status: str
    was_running: bool


class HealthRes(BaseModel):
    status: str
    detector: str  # 'hailo' | 'yolo' | 'none' | ...


# ------------------------------------------------------------------ Endpoints

@app.post("/track/start", response_model=TrackStartRes, summary="Tracking starten")
def track_start(request: TrackStartReq) -> TrackStartRes:
    try:
        return TrackStartRes(**visual.start_tracking(request.name))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/track/latest", response_model=TrackLatestRes, summary="Aktuelles Tracking-Ergebnis")
def track_latest() -> TrackLatestRes:
    return TrackLatestRes(**visual.get_latest())


@app.post("/track/stop", response_model=TrackStopRes, summary="Tracking beenden")
def track_stop() -> TrackStopRes:
    return TrackStopRes(**visual.stop_tracking())


@app.get("/health", response_model=HealthRes, summary="Server-Health-Check")
def health() -> HealthRes:
    return HealthRes(status="ok", detector=visual.active_detector())


# ------------------------------------------------------------------ Main

if __name__ == "__main__":
    HOST = os.environ.get("VISUAL_HOST", "127.0.0.1")
    PORT = int(os.environ.get("VISUAL_PORT", "7995"))
    print(f"[server] Starte auf {HOST}:{PORT}")
    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
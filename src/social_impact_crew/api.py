"""FastAPI wrapper exposing the AgentVerse REST contract.

Contract (stable across all AgentVerse episodes):
  POST /api/run  { "city": "..." }
       -> { city, coords, weather, pollution, aqi_level, meme }

The frontend (agentverse-frontend/) is framework-agnostic — only this file
changes per episode. For this episode it runs the CrewAI 3-agent crew.
"""

import os
import sys
from typing import Optional

import openlit
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .crew import SocialImpactCrew
from .llm import detect_provider, no_provider_message
from .tools import start_capture, take_capture

# Init observability before anything else so the crew/HTTP calls get traced.
openlit.init(application_name="social_impact_crew_api")


# ---------- Pydantic models (AgentVerse contract) ----------

class RunRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=80, example="Chennai")


class Coords(BaseModel):
    lat: float
    lon: float
    country: str = ""


class Weather(BaseModel):
    temp_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_kmh: Optional[float] = None
    precip_mm: Optional[float] = None


class Pollution(BaseModel):
    european_aqi: Optional[float] = None
    pm2_5: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    o3: Optional[float] = None
    co: Optional[float] = None


class RunResponse(BaseModel):
    city: str
    coords: Optional[Coords] = None
    weather: Weather
    pollution: Pollution
    aqi_level: str  # good | fair | moderate | poor | very_poor | extremely_poor
    meme: str


def _aqi_band(aqi: Optional[float]) -> str:
    """European AQI bands per EEA. >100 = extremely_poor (push-notif trigger)."""
    if aqi is None:
        return "unknown"
    if aqi < 20:
        return "good"
    if aqi < 40:
        return "fair"
    if aqi < 60:
        return "moderate"
    if aqi < 80:
        return "poor"
    if aqi < 100:
        return "very_poor"
    return "extremely_poor"


# ---------- App ----------

app = FastAPI(
    title="AgentVerse — Social Impact Crew API",
    version="0.1.0",
    description="CrewAI episode. Contract is stable across AgentVerse episodes.",
)

# Permissive CORS for local dev — the frontend runs on a different origin
# (file://, localhost:5500, etc). Tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    choice = detect_provider()
    return {
        "status": "ok",
        # choice.model already includes the provider prefix for litellm
        # providers (e.g. "groq/llama-..."), so just return it as-is.
        "llm": choice.model if choice else None,
        "provider": choice.provider if choice else None,
    }


@app.post("/api/run", response_model=RunResponse)
def run(req: RunRequest) -> RunResponse:
    # Tools write structured data into this context bucket as a side channel
    # while still returning LLM-friendly strings to the agents.
    start_capture()
    try:
        crew_obj = SocialImpactCrew().crew()
        result = crew_obj.kickoff(inputs={"city": req.city})
        captured = take_capture()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"crew run failed: {e}") from e

    pollution = Pollution(**(captured.get("pollution") or {}))
    return RunResponse(
        city=req.city,
        coords=Coords(**captured["coords"]) if "coords" in captured else None,
        weather=Weather(**(captured.get("weather") or {})),
        pollution=pollution,
        aqi_level=_aqi_band(pollution.european_aqi),
        meme=str(result.raw if hasattr(result, "raw") else result).strip(),
    )


def main() -> None:
    """Entry point for `run_api` script."""
    load_dotenv()
    if detect_provider() is None:
        sys.exit(no_provider_message())
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    print(f"AgentVerse API on http://{host}:{port}  (POST /api/run)")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

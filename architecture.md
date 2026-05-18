# Architecture — Social Impact Crew (AgentVerse Episode 1)

```mermaid
flowchart TB
    subgraph Frontend["agentverse-frontend/ (PWA, reusable)"]
        UI["WhatsApp-style Chat UI<br/>(index.html + app.js)"]
        SW["Service Worker<br/>(sw.js)"]
        Notif["Notifications<br/>(notifications.js)"]
        UI -->|"navigator.geolocation<br/>or ipinfo fallback"| GEO[(User Location)]
        UI -.->|"register"| SW
        SW -->|"every 30 min"| UI
    end

    subgraph Backend["social_impact_crew/ (this episode)"]
        API["FastAPI<br/>POST /api/run"]
        OPENLIT["OpenLIT<br/>auto-instrumentation"]
        subgraph Crew["CrewAI — Sequential Process"]
            A1["1. Weather Reporter<br/>(temp 0.4)"]
            A2["2. Pollution Analyst<br/>(temp 0.4)"]
            A3["3. Tamil Meme Writer<br/>(temp 0.9)"]
            A1 --> A2 --> A3
        end
        Tools["Custom Tools<br/>GeocodeTool, WeatherTool, PollutionTool"]
        Capture[("ContextVar<br/>tool outputs")]
    end

    subgraph External["External APIs (free, no key)"]
        Geo["Open-Meteo<br/>Geocoding"]
        Weather["Open-Meteo<br/>Weather"]
        AQ["Open-Meteo<br/>Air Quality"]
    end

    subgraph LLM["LLM Provider (BYOK)"]
        Groq["Groq / Gemini / OpenAI / Ollama<br/>(auto-detected in llm.py)"]
    end

    UI -->|"POST {city}"| API
    API --> OPENLIT
    OPENLIT --> Crew
    A1 --> Tools
    A2 --> Tools
    Tools --> Geo
    Tools --> Weather
    Tools --> AQ
    Tools -.->|"side-channel structured data"| Capture
    Capture -.-> API
    Crew --> Groq
    API -->|"{weather, pollution, meme, aqi_level}"| UI
    UI -->|"if aqi_level in {poor, very_poor, extremely_poor}"| Notif
```

## Why this shape

- **PWA is its own folder** because the same frontend will be reused across AgentVerse episodes (CrewAI, LangGraph, Google ADK, etc.). Only the backend changes per episode — the frontend talks to a fixed REST contract.
- **API contract** is deliberately framework-agnostic: `POST /api/run {city}` → `{weather, pollution, meme, aqi_level}`. Any future episode just needs to expose the same shape.
- **Tool side-channel via `ContextVar`** captures structured data without polluting LLM-facing tool outputs. The agents still see human-readable strings; the API gets typed dicts.
- **OpenLIT one-liner** auto-instruments LLM + HTTP calls so the user can wire up any OTLP-compatible backend (Grafana, Jaeger, OpenLIT UI, etc.) by setting env vars.
- **Sequential process** preserved for the educational CLI demo. The API runs the same crew end-to-end.

## API contract (locked across episodes)

**Request:** `POST /api/run`
```json
{ "city": "Chennai" }
```

**Response:** `200 OK`
```json
{
  "city": "Chennai",
  "coords": { "lat": 13.087, "lon": 80.278, "country": "India" },
  "weather": {
    "temp_c": 29.9,
    "feels_like_c": 35.7,
    "humidity_pct": 81,
    "wind_kmh": 12.9,
    "precip_mm": 0.0
  },
  "pollution": {
    "european_aqi": 30,
    "pm2_5": 14.1,
    "pm10": 18.0,
    "no2": 10.5,
    "o3": 76.0,
    "co": 323.0
  },
  "aqi_level": "fair",
  "meme": "Dei thambi, Chennai la 29.9 degree thermostata nu solren..."
}
```

**`aqi_level` values** (European AQI bands, per EEA):
- `good` (0–20)
- `fair` (20–40)
- `moderate` (40–60)
- `poor` (60–80)
- `very_poor` (80–100)
- `extremely_poor` (>100) ← frontend fires push notification at this level

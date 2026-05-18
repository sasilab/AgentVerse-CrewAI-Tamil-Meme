# AgentVerse API Contract

The **stable interface** every AgentVerse backend exposes. The shared PWA
(`agentverse-frontend/`) calls these endpoints. Match the schema exactly and
your backend works with the existing frontend, no changes needed.

---

## Endpoints

### `POST /api/run`

Run the agent crew for a given city; return weather + pollution + meme + aqi level.

**Request body:**
```json
{ "city": "Chennai" }
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `city` | string | yes | 1–80 chars |

**Response — 200 OK:**
```json
{
  "city": "Chennai",
  "coords": {
    "lat": 13.08784,
    "lon": 80.27847,
    "country": "India"
  },
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

| Field | Type | Notes |
|---|---|---|
| `city` | string | echoed back, may be normalised |
| `coords` | object \| null | present when geocoding succeeded |
| `coords.lat` | float | decimal degrees |
| `coords.lon` | float | decimal degrees |
| `coords.country` | string | may be empty |
| `weather.temp_c` | float \| null | °C |
| `weather.feels_like_c` | float \| null | apparent temperature, °C |
| `weather.humidity_pct` | float \| null | 0–100 |
| `weather.wind_kmh` | float \| null | |
| `weather.precip_mm` | float \| null | |
| `pollution.european_aqi` | float \| null | European AQI scale (EEA) |
| `pollution.pm2_5` | float \| null | µg/m³ |
| `pollution.pm10` | float \| null | µg/m³ |
| `pollution.no2` | float \| null | µg/m³ |
| `pollution.o3` | float \| null | µg/m³ |
| `pollution.co` | float \| null | µg/m³ |
| `aqi_level` | string enum | see table below |
| `meme` | string | freeform creative output; agents can tone this however they want |

**`aqi_level` enum** (computed from `pollution.european_aqi` per EEA bands):

| Value | AQI range | Frontend fires notification? |
|---|---|---|
| `good` | 0–20 | no |
| `fair` | 20–40 | no |
| `moderate` | 40–60 | no |
| `poor` | 60–80 | **yes** |
| `very_poor` | 80–100 | **yes** |
| `extremely_poor` | >100 | **yes** |
| `unknown` | `european_aqi` was null | no |

**Errors:**
- `400 Bad Request` — invalid body (city missing, too long, etc.)
- `500 Internal Server Error` — backend crashed during the agent run; response body has a `detail` field

### `GET /api/health`

Liveness + provider info. The frontend can call this on boot to confirm the backend is up.

**Response — 200 OK:**
```json
{
  "status": "ok",
  "llm": "groq/llama-3.3-70b-versatile",
  "provider": "groq"
}
```

| Field | Type | Notes |
|---|---|---|
| `status` | string | `"ok"` when healthy |
| `llm` | string \| null | full LiteLLM model string |
| `provider` | string \| null | short provider name |

---

## Examples

**cURL:**
```bash
curl -X POST http://localhost:8000/api/run \
  -H "content-type: application/json" \
  -d '{"city":"Chennai"}'
```

**Frontend (already implements this — for reference only):**
```javascript
const r = await fetch(`${backend}/api/run`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ city }),
});
const data = await r.json();
// data.aqi_level → maybe fire a notification
// data.meme → display in chat bubble
// data.weather, data.pollution → optional details strip
```

---

## Compliance checklist for a new backend

When building a new episode backend in a different framework (LangGraph, ADK, AutoGen, DSPy, ...), you only need to:

- [ ] Expose `POST /api/run` returning the JSON shape above
- [ ] Compute `aqi_level` from `european_aqi` using the band table above
- [ ] Expose `GET /api/health` returning `{status, llm, provider}`
- [ ] Enable CORS for whatever origin the frontend runs from (or `*` for dev)
- [ ] Use Open-Meteo (or any keyless data source) so learners don't need a weather/AQI API key
- [ ] Recommend: `openlit.init()` at app startup for free observability

Your framework can do whatever it likes inside `/api/run` — multi-agent crew, single-shot LLM call, state-machine, RAG pipeline, mixture of experts. The contract doesn't care. If the JSON shape matches, the frontend works.

---

## Versioning

If a future episode needs extra fields, **add them as optional** — never break existing ones. If you legitimately must break the contract, bump a `version` query parameter (`/api/run?v=2`) and gate the new shape behind it. The frontend should default to v1 until updated.

# Setup — Social Impact Crew (Episode 1)

How to run the full AgentVerse stack (this backend + the shared frontend) locally.

## Prerequisites

- **Python** 3.10 – 3.12 (3.12 tested)
- **A modern browser** (Chrome / Edge recommended for full PWA features)
- **One LLM key** — pick whichever is easiest:
  - **Groq** (free, fastest): https://console.groq.com/keys
  - **Gemini** (free tier): https://aistudio.google.com/apikey
  - **OpenAI** (paid): https://platform.openai.com/api-keys
  - **Ollama** (local, no key required): https://ollama.com/download

## 1. Clone & install the backend

```bash
git clone <repo> social_impact_crew
cd social_impact_crew

# Virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install — this also installs the `run_crew` and `run_api` scripts
pip install -e .
```

> ⚠️ **Don't run `pip install --upgrade pip` on Windows** inside a fresh venv —
> it can leave the venv with a broken pip (`WinError 32`). If you already did
> and it broke: `Remove-Item -Recurse -Force .venv`, then redo `python -m venv .venv`
> followed by `pip install -e .` without the upgrade step.

## 2. Set your LLM key

```bash
cp .env.example .env
# then edit .env and uncomment ONE of:
#   GROQ_API_KEY=gsk_...
#   GEMINI_API_KEY=...
#   OPENAI_API_KEY=sk-...
# OR run `ollama serve` and `ollama pull llama3.2` (no key needed)
```

The app auto-detects which key is set. Preference order if multiple are set:
**Groq → Gemini → OpenAI → Ollama**.

## 3. CLI quick check (optional but recommended first run)

```bash
run_crew                # auto-detects your city via IP, prompts to confirm
run_crew Bengaluru      # or pass a city
```

You'll see verbose CrewAI logs (tool calls, agent messages) and a final
Tanglish meme. Good signal that the backend is healthy before wiring up the
frontend.

## 4. Run the API server

```bash
run_api
# AgentVerse API on http://127.0.0.1:8000  (POST /api/run)
```

Sanity-check:

```bash
curl http://127.0.0.1:8000/api/health

curl -X POST http://127.0.0.1:8000/api/run \
  -H "content-type: application/json" \
  -d '{"city":"Chennai"}'
```

You should see the full contract response (`city`, `coords`, `weather`,
`pollution`, `aqi_level`, `meme`). See [API_CONTRACT.md](./API_CONTRACT.md) for
the schema.

## 5. Run the frontend

In a separate terminal:

```bash
cd ../agentverse-frontend
python -m http.server 5500
```

Open http://localhost:5500. Accept the location prompt → the chat fires
`/api/run` for your detected city and shows the meme. Type any other city in
the composer to ask again.

Click the ⚙ icon in the header to change the backend URL, override the city,
or adjust polling. Settings persist in `localStorage`.

---

## How-to: add a new LLM provider

The auto-detector handles Groq / Gemini / OpenAI / Ollama automatically. To
pin a specific model (this overrides auto-detect):

```bash
# in .env
MODEL=groq/llama-3.1-8b-instant
# or
MODEL=gemini/gemini-2.5-flash
# or
MODEL=gpt-4o-mini
# or
MODEL=ollama/mistral
```

Format follows [LiteLLM's `provider/model` convention](https://docs.litellm.ai/docs/providers).

To wire in a *new* provider not on the list above (e.g. Anthropic, hosted Mistral):
1. Add the env-var name + default model string to `DEFAULTS` in `src/social_impact_crew/llm.py`
2. Add the detection branch in `detect_provider()`
3. Update `no_provider_message()` so the friendly help mentions it

## How-to: add a new city

No code changes needed — type any city in the chat composer, or pass it as
an arg: `run_crew "São Paulo"`. The `GeocodeTool` resolves any city name to
lat/lon via Open-Meteo.

## How-to: enable real observability

OpenLIT auto-instruments LLM + HTTP calls. By default it sends OTLP to
`http://127.0.0.1:4318`. To actually see traces / metrics:

```bash
# Easiest: OpenLIT's own collector
docker run -d -p 4318:4318 -p 3000:3000 ghcr.io/openlit/openlit
# or any OTLP-compatible backend (Jaeger, Grafana Tempo, etc.)
```

Then open http://localhost:3000 (or whichever UI your collector ships) to see
spans for each agent step + LLM call.

To **silence** OpenLIT's startup logs when no collector is running:

```bash
# bash
export OTEL_LOG_LEVEL=error
# PowerShell
$env:OTEL_LOG_LEVEL = "error"
```

---

## Troubleshooting

### `WinError 32` during pip install on Windows
Pip upgrade collided with a file lock. Delete `.venv`, recreate, install without `--upgrade pip`.

### `Unable to initialize LLM with model 'groq/...'`
Missing `litellm`. Run `pip install litellm` or just `pip install -e .` again.

### `'Crew' object has no attribute 'plot'`
CrewAI 1.x removed `plot()`. Use the static `architecture.md` Mermaid diagram instead.

### Emojis in PowerShell render as `ðŸ‹`
Console encoding mismatch. The file is correct UTF-8. Fix the display:
```powershell
$env:PYTHONIOENCODING="utf-8"
```

### Browser says "geolocation denied"
The PWA falls back to IP-based detection automatically (via ipinfo.io). You
can also enter a city manually in the composer, or set a default in Settings.

### Notification didn't fire on a high-AQI city
- Did you grant notification permission? Check browser site settings.
- Is `aqi_level` actually in `{poor, very_poor, extremely_poor}`? Curl `/api/run` and check.
- Is the notification toggle ON in Settings?

### CORS error in browser console
`api.py` defaults to `allow_origins=["*"]`. If you tightened it, add your
frontend's origin to the allowlist.

### OpenLIT prints a wall of JSON on startup
Normal when no OTLP collector is reachable. Either run a collector or set
`OTEL_LOG_LEVEL=error` (see *enable real observability* above).

### Crew run takes >60s
Probably an LLM cold start. Groq is usually <10s, OpenAI 10–30s, Ollama depends
on hardware. If persistent: check `GET /api/health` and your network.

### `[CrewAIEventsBus] Warning: Event pairing mismatch`
Internal CrewAI 1.x telemetry warning. Cosmetic, ignore.

# Social Impact Crew — Weather + Pollution + Tamil Meme Writer

A 3-agent [CrewAI](https://docs.crewai.com/) crew that pulls live weather and
air-quality data for any city and turns it into a sarcastic Tanglish meme.

Part of **AgentVerse** by [@explainpannu](https://x.com/explainpannu) — an
educational series teaching AI agent frameworks through small social-impact
projects. One episode = one framework + one real-world problem.

> Previous episode: [BreezyBuddy](https://github.com/sasilab/BreezyBuddy) — a
> simple ReAct weather agent.

---

## What it does

```
You: "Chennai"
  │
  ▼
┌──────────────────────┐
│ Weather Reporter     │  → geocodes the city, fetches current weather
└──────────┬───────────┘
           │ (lat/lon + summary)
           ▼
┌──────────────────────┐
│ Pollution Analyst    │  → fetches AQI, PM2.5, PM10, NO2, O3
└──────────┬───────────┘
           │ (air-quality briefing)
           ▼
┌──────────────────────┐
│ Tamil Meme Writer    │  → writes a 4-6 line Tanglish meme
└──────────────────────┘
```

All data comes from **Open-Meteo** (free, no API key). The only key you need
is for the LLM.

## Tech stack

- **Framework:** CrewAI (latest)
- **LLM:** Bring-your-own-key — Groq / Gemini / OpenAI / Ollama, auto-detected from `.env`
- **Data APIs:** Open-Meteo (weather, air-quality, geocoding) + ipinfo.io (location)
- **Python:** 3.10 – 3.12

## Features

- **Intent detection** — two-layer classifier (regex fast-path + LLM fallback)
  routes each message to the right path: city query → full crew, casual
  chitchat → direct LLM, settings command → nudge. Stops "hi" from kicking off
  a 3-agent run and stops Tamil chitchat ("enne chellam") from fuzzy-matching
  random villages.
- **Safety guardrails** — rule-based AQI override fires *before* the LLM: when
  `european_aqi >= 100`, a hardcoded health alert is returned and the meme
  writer never gets to joke about hazardous air.
- **Emotion + consent override** — if you sound sick, tired, sad, anxious, or
  say "leave me alone", personality drops away and the reply is warm, brief,
  and nudge-free. Health and consent override personality.
- **Prompt-injection protection** — soft regex sanitiser neutralises common
  "ignore previous instructions" / "you are now" / "reveal system prompt"
  phrasings before they reach the model. Defence-in-depth, not a hard boundary.
- **6 personalities × 4 languages** — Sarcastic, Wholesome, Dad-jokes,
  Stoic-philosopher, Chaotic-genZ, Aunty-mode × English / Tanglish / Tamil /
  Hindi. Swap voices live from the Settings panel; no restart, no code edits.
- **BYOK via Settings panel (or .env)** — drop any one of `GROQ_API_KEY`,
  `GEMINI_API_KEY`, `OPENAI_API_KEY` into `.env`, or paste a key into the
  frontend Settings panel and it's used immediately (no restart). Ollama works
  with no key. Preference order: Groq → Gemini → OpenAI → Ollama.
- **Background AQI polling** — the frontend periodically calls `/api/run` to
  refresh the AQI pill so the badge stays current without user interaction.
- **Push notifications** — in-tab Notification API + service worker fire a
  local alert when the AQI crosses a threshold. No VAPID keys, no server-side
  push endpoint required.
- **City auto-detect** — on CLI startup, your city is guessed from your public
  IP (via [ipinfo.io](https://ipinfo.io), no key needed). Press Enter to
  accept, or type any other city to override. Pass a city on the CLI to skip
  the prompt entirely.

## Quickstart

```bash
# 1. Clone & enter
git clone <this-repo>
cd social_impact_crew

# 2. Virtual env
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 3. Install
pip install -e .

# 4. Add your LLM key
cp .env.example .env
# then edit .env and paste your GROQ_API_KEY (get one free at https://console.groq.com/keys)

# 5. Run
python -m social_impact_crew.main              # asks for a city
python -m social_impact_crew.main Bengaluru    # or pass it on the CLI
```

You'll get verbose CrewAI logs as each agent works, and the final meme
printed at the bottom.

## Switching the LLM

You don't need to pick a provider explicitly — just put your key in `.env` and
the app auto-detects it. All four supported providers:

| Provider | Free? | Env var to set | Default model |
|---|---|---|---|
| Groq | yes | `GROQ_API_KEY` | `groq/llama-3.3-70b-versatile` |
| Gemini | yes | `GEMINI_API_KEY` | `gemini/gemini-2.5-flash` |
| OpenAI | no | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Ollama | yes (local) | *(none — just run `ollama serve`)* | `ollama/llama3.2` |

If you want to pin a specific model, set `MODEL=<provider>/<model>` in `.env`.
That always wins over auto-detection. Format follows [LiteLLM's `provider/model` convention](https://docs.litellm.ai/docs/providers).

## Project layout

```
social_impact_crew/
├── pyproject.toml
├── .env.example
├── architecture.md             # Mermaid diagram + locked API contract
└── src/social_impact_crew/
    ├── main.py                 # CLI entry point + IP geolocation + OpenLIT
    ├── api.py                  # FastAPI wrapper — POST /api/run + /api/chat
    ├── crew.py                 # @CrewBase wiring
    ├── llm.py                  # provider auto-detection (BYOK) + runtime overrides
    ├── intent.py               # two-layer intent classifier (regex + LLM fallback)
    ├── personality.py          # 6 personalities × 4 languages voice blocks
    ├── preferences.py          # JSON-file user prefs (async lock + atomic write)
    ├── safety.py               # AQI safety override + prompt-injection sanitiser
    ├── config/
    │   ├── agents.yaml         # role / goal / backstory per agent
    │   └── tasks.yaml          # description / expected_output / context
    └── tools/
        └── custom_tool.py      # GeocodeTool, WeatherTool, PollutionTool
                                # + ContextVar side-channel for API capture
```

## Running as an API

```bash
run_api                # serves on http://127.0.0.1:8000
# POST http://127.0.0.1:8000/api/run   {"city": "Chennai"}
# POST http://127.0.0.1:8000/api/chat  {"message": "hi"}
# /api/run returns {city, coords, weather, pollution, aqi_level, meme}
```

## Frontend

The AgentVerse PWA frontend lives in its own repo:

**→ [github.com/sasilab/AgentVerse-Frontend](https://github.com/sasilab/AgentVerse-Frontend)**

It's a single static PWA reused across every AgentVerse episode. To connect it
to this backend:

1. Start this backend: `run_api` (serves on `http://127.0.0.1:8000`).
2. Clone & serve the frontend per its README.
3. Open the Settings panel in the PWA and point the API base URL at
   `http://127.0.0.1:8000`. Paste your LLM key, pick a personality and
   language, and you're done.

The `POST /api/run` contract is stable across every AgentVerse episode, so the
same frontend works against any episode backend.

## Observability

`openlit.init()` is called at the top of `main.py` and `api.py`. By default
it ships traces/metrics to `http://127.0.0.1:4318` (OTLP). To see them, run any
OTLP collector (Jaeger, Grafana Tempo, OpenLIT UI). No collector running = silent
no-op, nothing breaks.

## Why these design choices

- **Geocoding as a tool** (not hardcoded coords) so the meme works for *any*
  city you throw at it.
- **YAML configs** for agents and tasks so non-coders can tweak personalities
  and task prompts without touching Python.
- **Sequential process** because the meme literally depends on the upstream
  data — no point in running these in parallel.
- **Tools only where needed** — the meme writer has no tools because its job
  is pure creative writing over upstream context.

## License

MIT. Built for learning — fork it, remix it, make your own episode.

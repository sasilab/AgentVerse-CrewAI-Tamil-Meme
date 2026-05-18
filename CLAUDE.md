# AgentVerse — Social Impact AI Agents

## About
@explainpannu's (Sasi) educational project teaching AI agent frameworks by
building social impact agents. Each episode = one framework + one real-world
problem.

## Current Episode: CrewAI + Weather + Pollution + Tamil Meme Writer
A 3-agent CrewAI crew that turns live weather + AQI data for any city into a
sarcastic Tanglish meme:
1. **Weather Reporter** — fetches weather from Open-Meteo API (free, no key)
2. **Pollution Analyst** — fetches AQI from Open-Meteo Air Quality API (free, no key)
3. **Sarcastic Tamil Meme Writer** — takes both outputs and writes funny Tanglish commentary

## Tech Stack
- **Framework:** CrewAI (latest)
- **LLM:** Bring-your-own-key — Groq / Gemini / OpenAI / Ollama, auto-detected from `.env`
- **Data APIs:** Open-Meteo (weather, air-quality, geocoding) + ipinfo.io (location)
- **Python:** 3.10 – 3.12

## Rules (apply to all code in this repo)
- Keep code simple and beginner-friendly — this is educational content
- Add comments explaining WHY, not just WHAT
- Max 200 lines per file
- Use CrewAI CLI project structure (agents.yaml, tasks.yaml, crew.py, main.py)
- Custom tools for weather and pollution in `tools/custom_tool.py`
- No paid APIs for data — only the LLM needs a key (and even that's optional via Ollama)

## Session Memory
- **SESSION.md** is the running log of what's done, what's working, and what's next
- Update SESSION.md after every major step (file created, feature added, run completed, blocker hit)
- This file (CLAUDE.md) captures *persistent* decisions; SESSION.md captures *current* state

## Decisions Made (so far)
- **IP geolocation via ipinfo.io** (HTTPS, no key, 50k/month free) over ip-api.com (HTTP only)
- **Provider auto-detection lives in `llm.py`** as its own module — both `main.py` (startup check) and `crew.py` (agent build) import from it
- **Provider preference order:** explicit `MODEL` env var → Groq → Gemini → OpenAI → local Ollama (free providers first)
- **Geocoding as a CrewAI tool**, not hardcoded coords — so the meme writer works for any city
- **Sequential process** (weather → pollution → meme) because each step's output is the next step's input
- **Meme writer has no tools** — it's pure creative writing over upstream task context
- **City default = IP-detected city**, with user override via prompt or CLI arg
- **Fail-fast on missing LLM key** at startup with a friendly message listing all 4 providers and where to get keys
- **Per-agent temperature** via `build_llm(temperature=...)` — data agents stay at 0.4, meme writer at 0.9 for punchier output
- **Few-shot examples in the meme task description** — model needs 3 concrete example memes to learn the trending-Tamil-meme-page tone; without them it just translates the analyst's report
- **`litellm>=1.50.0` is a hard dep** — CrewAI 1.x dropped Groq from its native providers list, so LiteLLM is required for the default Groq path
- **No `crew.plot()`** — method was removed in CrewAI 1.x (visualization moved to `Flow.plot()`); call removed from main.py

## Previous Episode
BreezyBuddy (github.com/sasilab/BreezyBuddy) — simple ReAct weather agent

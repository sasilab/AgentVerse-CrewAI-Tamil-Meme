# Session Log — Social Impact Crew

> Running log of what's been done, what's working, and what's next.
> Update after every major step.

**Last updated:** 2026-05-18

---

## Done

### Project scaffolding
- `social_impact_crew/` created with CrewAI CLI-style layout
- `pyproject.toml` — deps: `crewai[tools]`, `requests`, `python-dotenv`
- `.env.example`, `.gitignore`
- `src/social_impact_crew/__init__.py` and `tools/__init__.py`

### Tools (`tools/custom_tool.py`)
- `GeocodeTool` — Open-Meteo geocoding (city → lat/lon)
- `WeatherTool` — Open-Meteo current weather (temp, humidity, wind, precip)
- `PollutionTool` — Open-Meteo Air Quality (European AQI, PM2.5, PM10, NO2, O3, CO)
- All Pydantic-typed args, 15s HTTP timeout

### Agents + tasks
- `config/agents.yaml` — Weather Reporter, Pollution Analyst, Tamil Meme Writer
- `config/tasks.yaml` — chained via `context:` (weather → pollution → meme)

### Crew wiring (`crew.py`)
- `@CrewBase` class, sequential process, verbose mode
- Each agent built with `build_llm()` from `llm.py`

### Entry point (`main.py`)
- Loads `.env`, runs startup provider check, fails fast with friendly message
- `_detect_city_from_ip()` via ipinfo.io (5s timeout, silent fallback)
- `_prompt_city()`: CLI arg > user input > IP-detected default > "Chennai"
- Calls `crew.plot()` then `crew.kickoff(inputs={"city": city})`

### LLM provider auto-detection (`llm.py`)
- `detect_provider()` returns `ProviderChoice(provider, model, source)`
- Order: `MODEL` env var → `GROQ_API_KEY` → `GEMINI_API_KEY` → `OPENAI_API_KEY` → local Ollama probe
- `no_provider_message()` lists all 4 providers + where to get a key
- Ollama detected via 1s ping to `localhost:11434` (or override with `OLLAMA_BASE_URL`)

### Documentation
- `README.md` with quickstart, provider table, design notes
- `claude.MD` cleaned up + Decisions section
- This file

---

## Working

- All code files compile (syntactically valid; not yet executed)
- File structure matches CrewAI CLI conventions
- Every file under 200-line limit per project rules

## Not Yet Tested

- IP geolocation (live run used CLI arg `Chennai`, skipping the IP path)
- Gemini / OpenAI / Ollama provider branches (only Groq exercised)
- Interactive `_prompt_city()` flow (no TTY in subprocess; CLI arg path tested)

---

## Known Issues

- **`[CrewAIEventsBus] Warning: Event pairing mismatch`** lines in output — internal CrewAI telemetry warnings, not errors. Run still succeeds. Not actionable.
- **Meme sometimes repeats its punchline** (e.g. "mask podu illa" + "Mask ah podu da" in v2 output) — model occasionally over-extends the health tip. Could mitigate with a hard "max 6 lines, stop after the health tip" rule, or a post-processing trim.
- **Windows terminal mangles emoji output** in PowerShell — the meme file is correct UTF-8, but the console renders cp1252 garbage. Reading the output via the Read tool shows it cleanly. Pure terminal-display issue.

---

## Next

1. ~~install + live run~~ ✅ ~~meme writer temp 0.9 + few-shot examples~~ ✅ ~~remove dead crew.plot()~~ ✅
2. **Test:** interactive run (TTY) to verify the IP-detected default-city prompt works
3. **Test:** other providers (Gemini / Ollama) — only Groq exercised so far
4. **Optional follow-ups** (not started):
   - Add a "compare two cities" mode
   - Add cron/loop scheduling for daily meme
   - Push to GitHub as the next AgentVerse episode

---

## Change Log

- **2026-05-18 (initial):** scaffolded project, added IP geolocation + BYOK provider auto-detection, created session memory files (CLAUDE.md cleanup + this SESSION.md)
- **2026-05-18:** user added Groq key to `.env`; deleted broken `.venv` and recreated cleanly (pip working); kicked off `pip install -e .` in background
- **2026-05-18:** install succeeded (crewai 1.14.4); first live run failed — CrewAI 1.x doesn't ship Groq as a native provider, needs litellm. Added `litellm>=1.50.0` to pyproject.toml and installed.
- **2026-05-18:** ✅ live end-to-end run for Chennai succeeded. All 3 agents ran, tools called Open-Meteo correctly (lat 13.08784, lon 80.27847; AQI 30; temp 29.9°C feels 35.7°C). Tanglish meme produced. `crew.plot()` soft-failed (method removed in CrewAI 1.x).
- **2026-05-18:** v2 of meme writer — `build_llm()` now accepts `temperature` param; meme writer set to 0.9; meme_task description now includes 3 example memes + emoji rule + health-tip ending. Removed dead `crew.plot()` call from main.py. ✅ Re-run produced a noticeably punchier meme that picked up "Dei thambi" opener, "thermostata kaataadhu" trope, and "slow poison" callback from the examples. Still slightly repetitive on the mask tip.
- **2026-05-18:** ✅ Delhi stress test — AQI 342 (Extremely Poor), PM2.5 159, PM10 756. Meme handled the severity well: 🤢 on the AQI, 💀 on the PM10, layered health tip (mask + AC + skip outdoor exercise + see a doctor). Confirms the meme writer scales tone with the data, doesn't just parrot one template.
- **2026-05-18:** Delhi run #2 (same code, temp 0.9 → output varies). New meme used "corona virusum PM10 virusum enna da difference ah" — borderline edgy but PG. Variance is expected at this temperature.
- **2026-05-18:** ✅ Pre-push security audit completed. `.env` gitignored, no hardcoded secrets in source, only project files would be committed (12 files: configs, code, .gitignore, README, pyproject, .env.example).
- **2026-05-18:** Repo restructuring for push — moved `CLAUDE.md` + `SESSION.md` from AgentVerse root into `social_impact_crew/` so they ship with the episode repo (option A from the audit). Added a top-level `.gitignore` at AgentVerse root covering `.env`, `.venv/`, `__pycache__/`, `.crewai/`, `*.pyc`, `.DS_Store` for any future episode subfolders.

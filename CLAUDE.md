# AgentVerse — Claude Code Project Memory

> Persistent instructions for any future Claude Code session working on the
> AgentVerse series. Read this first; it links to the other docs.
>
> **Canonical copy lives here, at the AgentVerse root.** Each episode folder
> also keeps an identical copy so the episode repo is self-contained when
> pushed. Edit at the root, then `cp` into each episode (or vice-versa) when
> something changes.

## About

**AgentVerse** is @explainpannu's (Sasi) educational series teaching AI agent
frameworks through small social-impact agents. Each **episode** = one
framework + one real-world problem. The frontend is built once and reused;
only the backend changes per episode.

## Repo shape

```
multi-agent/                       ← AgentVerse root (this folder)
├── .gitignore                     ← protects every episode subfolder
├── CLAUDE.md                      ← canonical (this file)
├── API_CONTRACT.md                ← canonical
├── EPISODES.md                    ← canonical
├── agentverse-frontend/           ← REUSABLE PWA — one for every episode
└── <episode>/                     ← each is its own publishable repo
    ├── CLAUDE.md                  ← copy of canonical
    ├── API_CONTRACT.md            ← copy of canonical
    ├── EPISODES.md                ← copy of canonical
    ├── SETUP.md                   ← episode-specific
    └── ...
```

## The contract that ties everything together

Every episode backend exposes the same REST surface. See **[API_CONTRACT.md](./API_CONTRACT.md)** for the schema, examples, and a compliance checklist for new backends.

**TL;DR:**
```
POST /api/run  { "city": "..." }
   → { city, coords, weather, pollution, aqi_level, meme }
```

The frontend (`agentverse-frontend/`) calls this contract verbatim. Don't
break the JSON shape. Add optional fields if you need to extend.

## Episodes shipped & planned

See **[EPISODES.md](./EPISODES.md)** for what was built, what worked, what didn't.

| # | Name | Framework | Status |
|---|---|---|---|
| EP00 | BreezyBuddy | ReAct (custom) | 🟢 shipped (pre-contract) |
| EP01 | Social Impact Crew | CrewAI 1.x | 🟢 shipped, contract-compliant |
| EP02+ | _planned_ | LangGraph / ADK / AutoGen / DSPy / ... | 🔴 |

## Architecture decisions (and WHY)

### Cross-cutting

- **Separate repo per episode** — each framework should stand alone so learners can clone just the one they're studying. Reusing the frontend means only the backend changes per episode, which is the whole pedagogical point.
- **Frontend in its own folder, not nested in any episode** — `agentverse-frontend/` is reusable. Coupling it to one backend would force a fork per episode.
- **Stable REST contract over streaming/RPC/MCP** — anyone can ship a backend in 30 minutes if they only need to match a JSON shape. Fancier protocols add complexity that doesn't pay off for an educational series.
- **AQI as the universal "social impact" lens** — gives every episode a real-world health hook beyond the toy demo.
- **Docs are duplicated, not symlinked** — symlinks are flaky on Windows and break when an episode is cloned standalone. Worth the small drift cost.

### Episode-internal (current pattern from EP01)

- **BYOK LLM with auto-detect** — drop any one of `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY` into `.env`, or run Ollama locally. App picks the first one it finds. Free providers ranked first. Centralised in a single `llm.py` module.
- **Tool side-channel via `ContextVar`** — tools return human-readable strings to the LLM AND write structured dicts to a request-scoped contextvar. Lets FastAPI return typed JSON without re-parsing LLM text. *Why:* parsing LLM-formatted text is brittle; running tools twice wastes API calls.
- **Per-agent temperature** — data/analyst agents stay at 0.4 (factual), creative agents at 0.9 (varied). *Why:* one-size-fits-all temperature either makes data agents hallucinate or makes creative agents dull.
- **Few-shot examples in the task description** — without them, models translate the input into the target voice but miss the *form*. With 3 concrete examples they pick up the meme-page rhythm.
- **OpenLIT for observability** — one-line `openlit.init()`. Auto-instruments LLM + HTTP. Silent no-op without an OTLP collector. *Why:* free, ungated, works with any OTLP backend; beats hand-rolled logging.
- **In-tab Notification API + service worker over Web Push** — mirrors BreezyBuddy. Web Push needs VAPID keys and a server endpoint, which is a lot of yak-shaving for an educational project.
- **Pre-resolve coordinates in `api.py`/`main.py`, pass `{lat}`/`{lon}` as kickoff inputs** — the weather/pollution agents used to extract coords from the geocode tool's text output. The LLM would non-deterministically hallucinate coords instead of waiting for the tool ("Coburg" → Coburg VIC Australia, or `lat=0, lon=0`). The fix: do geocoding *deterministically* in the API/CLI layer (a direct `GeocodeTool()._run()` call, no LLM), then pass the resolved coords as task inputs. Agents still call the weather/AQI tools — they just receive verified args. *Generalises to other frameworks:* never let an LLM thread data between tools via free-text if you can pre-compute and pass it as input.
- **No `{city}` (or any input variable) in `agents.yaml` — only in `tasks.yaml`** — CrewAI's interpolation of agent `role`/`goal`/`backstory` is unreliable across runs; the LLM sometimes garbles literal `{city}` into nonsense ("for what is your name?"). Task-description interpolation works fine. Keep agent personas generic; put context-specific variables in tasks only.
- **Rule-based safety gate runs BEFORE the LLM** (`safety.py::aqi_safety_override`). When `european_aqi >= 100` we return a hardcoded health alert and the meme writer never gets a chance to joke about it. *Why:* safety must never depend on a model. Mirrored directly from BreezyBuddy's `check_extreme_weather` pattern.
- **Personality + language as runtime inputs, NOT in YAML** — they're interpolated into the meme task's description at `kickoff(inputs={"personality_block": …, "language_block": …})`. Source of truth is `personality.py` (6 personalities, 4 languages). Lets the Settings panel switch voices without touching agent configs.
- **JSON-file preferences (`data/user_preferences.json`)** — single-user local app, no DB needed. Async lock + atomic rename on write (BreezyBuddy pattern). Gitignored everywhere because it contains the BYO API key in plain text.
- **BYOK via Settings panel, NOT env-only** (`llm.py::set_runtime_overrides`) — the API request reads user prefs and sets a `ContextVar` BEFORE `kickoff()`. `build_llm()` honours the override and passes `api_key=…` directly to the `LLM` constructor. Env vars (`GROQ_API_KEY` etc.) remain as a fallback for the CLI path. This means a fresh clone + drop the key in Settings → it works, no restart, no .env editing.
- **Prompt-injection sanitiser** (`safety.py::sanitize_user_input`) — soft regex layer that replaces "ignore previous instructions" / "you are now" / "reveal system prompt" phrases with `[neutralized: …]` markers. Direct port from BreezyBuddy. Not a security boundary; defence-in-depth.
- **Two-layer intent classifier** (`intent.py`) before any geocode/crew call. (1) Fast regex path for obvious greetings ("hi", "vanakkam"), settings commands ("change language"), and Tamil/Tanglish chitchat ("enne thangam", "chellam"). (2) LLM fallback (temperature 0, one short call) for ambiguous messages that also EXTRACTS the city name. *Why:* without this, every typed message went through geocoding and Open-Meteo fuzzy-matched casual Tamil ("enne chellam") to random small Indian towns ("Rasipuram"), then ran the full crew on bogus data.
- **`POST /api/chat` vs `POST /api/run`** — `/api/chat` takes a freeform message and routes by intent (city query → crew, casual → direct LLM call, settings → nudge). `/api/run` keeps the strict `{city}` contract for programmatic use (AQI pill refresh, background polling, future episodes calling each other). Frontend's chat composer uses `/api/chat`; the pill click and the notification poll use `/api/run`.
- **Casual chat is a direct LLM call, NOT the crew** (`api.py::_casual_reply`) — same personality + language as the meme path, no tools, no agents. Crews are overkill for "hi". Keeps casual replies under a second on Groq.
- **Geocode-match validation** (`intent.py::is_plausible_geocode`) — even when intent says CITY, the returned match must be either name-similar (`SequenceMatcher >= 0.5`) or a substring/token overlap with the input. Rejects "enne chellam → Rasipuram"-class fuzzy fails. If validation fails, we fall back to the casual reply path instead of erroring — friendlier UX.

## Known issues (and fixes)

| Issue | Cause | Fix |
|---|---|---|
| `pip install -e .` fails on Windows with `WinError 32` | File lock on `urllib3/__pycache__` because `pip --upgrade pip` is uninstalling itself mid-process | Skip the pip upgrade; nuke and recreate `.venv` |
| `Unable to initialize LLM with model 'groq/...'` | CrewAI 1.x dropped Groq from native providers | Hard-dep on `litellm>=1.50.0` |
| `'Crew' object has no attribute 'plot'` | `plot()` moved to `Flow` in CrewAI 1.x | Don't call it; use the static `architecture.md` Mermaid diagram |
| `[CrewAIEventsBus] Warning: Event pairing mismatch` | Internal telemetry warning in CrewAI 1.x | Cosmetic, ignore |
| Emojis in PowerShell render as `ðŸ‹` | Console encoding is cp1252; file is UTF-8 | `$env:PYTHONIOENCODING="utf-8"` per session |
| OpenLIT prints a wall of JSON on startup | No OTLP collector reachable at `:4318` (default) | Run a collector, or set `OTEL_LOG_LEVEL=error` |
| Creative agent occasionally repeats its punchline at temp 0.9 | High temperature + few-shot can overshoot | Acceptable variance; lower temp if it becomes a problem |
| Weather returned for the wrong city, or `lat=0,lon=0` to pollution tool | LLM hallucinated tool args instead of waiting for upstream tool output (e.g. weather called with Coburg VIC AU coords for the German city) | Pre-resolve coords deterministically before kickoff; pass `{lat}`/`{lon}` as task inputs. See the "Pre-resolve coordinates" architecture decision. |
| Agent role shows "for what is your name?" instead of city | `{city}` interpolation in `agents.yaml` is unreliable in CrewAI 1.x | Don't put input variables in agent `role`/`goal`/`backstory`. Put them only in `tasks.yaml`. |

## Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Episode folder | `snake_case`, lowercase, descriptive | `social_impact_crew/` |
| Episode repo on GitHub | matches folder name (or `PascalCase` if framework-named) | `sasilab/social-impact-crew` |
| Python package | `snake_case`, matches folder | `social_impact_crew` |
| Env vars | `UPPER_SNAKE` | `GROQ_API_KEY`, `OLLAMA_BASE_URL` |
| Frontend assets | lowercase, descriptive | `notifications.js`, `icon.svg` |
| API routes | `kebab-case` under `/api/` | `/api/run`, `/api/health` |
| JSON field names | `snake_case` | `aqi_level`, `feels_like_c` |

## Rules for every episode

1. **Max 200 lines per file.** If you need more, split.
2. **Comments explain WHY, not WHAT.** Names should tell you what.
3. **No paid APIs for data.** Only the LLM needs a key (and Ollama makes even that optional).
4. **`.env` for secrets, never committed.** Both root and episode `.gitignore` enforce this.
5. **Beginner-friendly first.** Production hardening is fine but not at the cost of clarity.
6. **Episode self-contained.** Push the episode folder; it should run with the README + SETUP.md alone.
7. **Match `API_CONTRACT.md` exactly.** If the JSON shape changes, the frontend breaks for every episode. Add optional fields rather than breaking existing ones; bump a `version` query param if you must break.
8. **Document every non-obvious decision** in the *Architecture decisions* section above. Future-you and future-Claude will thank you.

## Adding a new episode

1. `cp -r social_impact_crew/ <new_episode_folder>/`, rename `pyproject.toml`'s `name` and script entries.
2. Replace `crew.py` (or equivalent) with the new framework's idiom. Keep `tools/custom_tool.py`, `llm.py`, and `api.py` mostly unchanged — they're framework-agnostic.
3. The `api.py` handler must still return the contract from `API_CONTRACT.md`. The `ContextVar` capture pattern works for any framework whose tools you can wrap.
4. Add a row to the table in **§Episodes shipped & planned** above.
5. Add a full entry to `EPISODES.md` (use the template at the bottom of that file).
6. If you made a new architectural decision, add it to **§Architecture decisions** above.

## Keeping these docs in sync

Three files are duplicated between the AgentVerse root and each episode folder:

- `CLAUDE.md`
- `API_CONTRACT.md`
- `EPISODES.md`

When you edit one, mirror it. From the root:

```bash
# macOS / Linux / Git Bash
for f in CLAUDE.md API_CONTRACT.md EPISODES.md; do
  for ep in social_impact_crew/ <other_episodes>/; do
    cp "$f" "$ep"
  done
done
```

```powershell
# PowerShell
foreach ($f in 'CLAUDE.md','API_CONTRACT.md','EPISODES.md') {
  foreach ($ep in 'social_impact_crew') { Copy-Item $f "$ep/" }
}
```

The episode-specific `SETUP.md` lives only in the episode folder — don't copy it up to root.

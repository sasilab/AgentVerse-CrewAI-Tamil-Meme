# AgentVerse Episodes

Each episode = one framework + one social-impact problem. The backend changes
per episode; the frontend (`agentverse-frontend/`) is reused.

## Status legend

- 🟢 **Shipped** — works end-to-end, repo is public
- 🟡 **In progress** — code exists, not fully tested or published
- 🔴 **Planned** — concept only

---

## EP00 — BreezyBuddy

| | |
|---|---|
| **Framework** | ReAct (custom Python loop, no framework abstraction) |
| **Problem** | "What's the weather?" — gentle on-ramp to agents |
| **LLM** | BYO (Groq supported) |
| **Tools** | Weather forecast tool |
| **Observability** | none |
| **Repo** | https://github.com/sasilab/BreezyBuddy |
| **Status** | 🟢 Shipped |
| **Contract** | ❌ Pre-AgentVerse — uses bespoke `/api/chat` and tool endpoints, not `/api/run` |

**What it taught:** the basic ReAct loop, tool-calling fundamentals, a vanilla-JS chat frontend with service-worker notifications. The frontend patterns from BreezyBuddy were extracted into `agentverse-frontend/` for reuse from EP01 onwards.

---

## EP01 — Social Impact Crew

| | |
|---|---|
| **Framework** | CrewAI 1.14.4 (with `litellm` for Groq compatibility) |
| **Problem** | Live weather + air-quality → sarcastic Tanglish meme with a hidden health tip |
| **LLM** | BYOK auto-detect: Groq (default), Gemini, OpenAI, Ollama |
| **Tools** | `GeocodeTool`, `WeatherTool`, `PollutionTool` — all Open-Meteo (no key) |
| **Observability** | OpenLIT one-liner (OTLP) |
| **Folder** | `social_impact_crew/` |
| **Status** | 🟢 Shipped — first AgentVerse-contract-compliant episode |
| **Contract** | ✅ Matches `API_CONTRACT.md` |

**Architecture highlights:**
- 3 agents in sequential process: Weather Reporter → Pollution Analyst → Tamil Meme Writer
- Per-agent temperature (data agents 0.4, meme writer 0.9)
- Few-shot meme examples baked into `tasks.yaml`
- Tools write structured data to a `ContextVar` side-channel so the API returns typed JSON without re-parsing LLM text
- Frontend uses `agentverse-frontend/` as-is

**What worked:**
- Few-shot examples transformed flat translations into actual meme-page voice
- Tool `ContextVar` approach: clean separation between LLM-facing strings and API-facing dicts
- BYOK detection + free-providers-first ordering: zero friction for learners
- OpenLIT one-liner: legitimately one line, just works
- Static Mermaid diagram (`architecture.md`) replaced `crew.plot()` cleanly

**What didn't (and why):**
- `crew.plot()` from the original brief — removed in CrewAI 1.x; replaced with a static `architecture.md`
- Groq direct connection — needed `litellm` as a hard dep because CrewAI 1.x dropped Groq from its native providers
- Initial meme tone — model just translated the analyst output into Tanglish; fixed with few-shot examples + temperature 0.9
- Meme occasionally repeats the punchline at temp 0.9 — acceptable variance; lower temp would dampen the voice

**Test results:**
- **Chennai** (AQI 30, "fair"): clean meme, references real numbers, includes mask tip
- **Delhi** (AQI 342, "extremely_poor"): meme escalated tone (🤢 and 💀 emojis), layered health advice (mask + AC + skip outdoors + see a doctor). Confirms the model scales tone with the data, doesn't just parrot one template.

**Lessons for future episodes:**
- Always run a high-extreme and low-extreme test (e.g. Chennai vs Delhi) **and a non-obvious city in a different region** (e.g. Coburg, Germany) to verify the creative agent isn't stuck on one tone AND that the data path isn't silently using the wrong coordinates.
- **Never trust an LLM to thread data between tools via a free-text string.** Discovered when EP01's weather agent hallucinated coordinates ("Coburg" → Melbourne suburb at 37.82, 145.07) instead of waiting for the geocode tool's output. Fix: pre-compute deterministically in the API/CLI layer, pass values as task inputs. See `CLAUDE.md § Pre-resolve coordinates` decision.
- **Don't put input variables in `agents.yaml`.** CrewAI 1.x interpolates `{vars}` in tasks reliably but in agent `role`/`goal`/`backstory` only sometimes — literal `{city}` can survive into the prompt and confuse the model.
- **Adopt BreezyBuddy DNA wholesale for the user-facing layer.** Mid-episode rebuild: replaced the minimalist PWA with a full BreezyBuddy-style settings panel + auto-save + permission banner + background mode + safety gate + 6 personalities + 4 languages. The cross-episode AgentVerse API contract stayed locked; the *internal* config layer matched a proven pattern instead of reinventing it.
- **Safety gate before LLM, every time.** EP01 now refuses to joke when `european_aqi >= 100` — the meme writer never sees the request; api.py returns a hardcoded N95 alert with `kind: "safety"`. The LLM is a liability for life-safety messaging.
- **BYOK via Settings, not env.** Users paste their key in the in-app Settings panel and it persists to `data/user_preferences.json`. The crew picks it up on the next request via a ContextVar — no restart, no .env editing. Future episodes inherit this for free by reusing `preferences.py` + `llm.set_runtime_overrides()`.
- ContextVar side-channel pattern transfers to any framework where you control the tool layer.
- Free-tier LLM (Groq) is plenty fast for a 3-agent sequential crew (~10-20s end-to-end).

**Test results (post-BreezyBuddy-rebuild, 2026-05-19):**
- **Coburg / sarcastic_meme / Tanglish:** 8.9°C, AQI 22 (fair). Meme references real temp + asthma (from saved `sensitive_groups`).
- **Coburg / caring_friend / English:** same numbers, completely different warm tone in plain English. Confirms personality + language switch at runtime.
- **Delhi / any personality:** AQI 324 → safety override fires, returns hardcoded N95 alert with `kind: "safety"`. LLM is bypassed.
- Coords for all three are pre-resolved deterministically (no hallucination).

**Test results (post-intent-classifier, 2026-05-19):**
Eight messages through `/api/chat`, sarcastic_meme + Tanglish:

| Input | intent_source | Routed to | Kind |
|---|---|---|---|
| `hi` | `fast:casual` | direct LLM, in-character | casual |
| `enne thangam` | `fast:casual` | direct LLM, "Dei, enne thangam nu solraen…" | casual |
| `how are you?` | `fast:casual` | direct LLM, "I'm good da, just watching…" | casual |
| `change my language to Tamil` | `fast:settings` | fixed nudge to ⚙️ | settings |
| `Chennai` | `llm:city` | crew run, AQI 30 fair | chat |
| `what is the weather in Mumbai please?` | `llm:city` (city extracted: "Mumbai") | crew run, AQI 58 moderate | chat |
| `enne chellam?` | `fast:casual` (never geocodes) | direct LLM | casual |
| `Delhi` | `llm:city` | crew run + safety override (AQI 331) | safety |

The previously-broken "enne chellam → Rasipuram" case is killed at the fast-path layer — it never hits geocoding. If something somehow makes it past intent classification, the `is_plausible_geocode` similarity check is the second line of defence (and on validation failure, we fall back to casual reply instead of erroring).

---

### Session 2026-05-19 — comprehensive log

**What shipped today (in roughly the order it happened):**

1. **Repo restructure for the AgentVerse series** — moved `CLAUDE.md`/`SESSION.md` into `social_impact_crew/`, added root-level `.gitignore`, established the duplicate-docs pattern (CLAUDE/API_CONTRACT/EPISODES at root *and* in each episode). Cleaned canonical docs (no more SESSION.md scratchpad).
2. **Coordinate-passing bug fixed** — pre-resolve coords in `api.py`/`main.py`, pass `{lat}`/`{lon}` as kickoff inputs. Stops the weather agent hallucinating "Coburg, Victoria" for the German Coburg. Stripped `{city}` from `agents.yaml` (kept it in `tasks.yaml` where interpolation is reliable).
3. **BreezyBuddy DNA rebuild** — full frontend replacement: WhatsApp UI, settings panel with auto-save, 6 personalities, 4 languages, BYOK Settings, AQI alerts, Background Mode, service worker, permission banner. Backend gained `preferences.py` (JSON store with async lock), `personality.py` (6 personality blocks × 4 language blocks), `safety.py` (AQI override + injection sanitizer), runtime LLM overrides via ContextVar in `llm.py`, plus 5 new endpoints (`/api/settings` GET+POST, `/api/test-llm`, `/api/geocode`, `/api/nudge`, `/api/personalities`).
4. **Frontend 405 / Model-dropdown / SW-cache fixes** — three issues fixed in one pass:
    - `sw.js` now nukes all caches on `activate` (defensive against pre-rebuild `agentverse-v1` cache).
    - CORS dropped `allow_credentials=True` (incompatible with `allow_origins=["*"]` per spec).
    - Model field became a `<datalist>` autocomplete with curated models per provider, auto-fills sensible default on provider switch.
5. **Intent classifier added** — new `intent.py` module with a fast regex classifier (catches `hi`, `enne thangam`, `change language`, `?`, etc.) + an LLM fallback that also *extracts* the city name from sentences like "what's the weather in Mumbai please". `POST /api/chat` is the new freeform endpoint; `POST /api/run` stays as the strict `{city}` contract for programmatic use. Casual replies are direct LLM calls in the chosen personality + language (no crew, ~1s on Groq).
6. **Geocoder validation** — `is_plausible_geocode()` checks the returned name is name-similar (≥0.5 SequenceMatcher) or has a token overlap with the input. Fuzzy "enne chellam → Rasipuram"-class matches are rejected and fall back to casual reply instead of erroring.
7. **Emotion + consent rules** baked into both the meme task description and the casual-reply system prompt: sick/tired/sad/anxious → drop personality, reply warmly, no nudge. Fast classifier catches the obvious phrases up front.
8. **Prompt injection sanitizer** (`safety.py::sanitize_user_input`) — regex layer that replaces "ignore previous", "you are now", "reveal system prompt" with `[neutralized: …]` markers before the LLM sees the input. Direct port from BreezyBuddy.
9. **Gemini 2.5 migration** — `gemini-2.0-flash` deprecated by Google. Updated everywhere: `llm.py` DEFAULTS, `settings.js` dropdown (added `gemini-2.5-pro` as a second suggestion), `.env.example`, `README.md`, `SETUP.md`. Default is now `gemini/gemini-2.5-flash`.

**Final end-to-end test (after all of the above) — 8 messages through `/api/chat`, sarcastic_meme + Tanglish:** see the "post-intent-classifier" table above. Every routing decision correct; Delhi's AQI 331 triggers the hardcoded safety alert; Coburg's 9°C matches real local weather; the previously-broken Tamil chitchat cases land in the casual-reply path with in-character responses.

**Stack at session end:**
- Backend: FastAPI + CrewAI 1.14.4 + LiteLLM + OpenLIT, all behind `run_api` on `127.0.0.1:8000`. Hosts the frontend at `/`.
- Frontend: vanilla JS PWA at `multi-agent/agentverse-frontend/` (reusable across episodes).
- Persistence: `data/user_preferences.json` (gitignored, contains BYO key in plain text).
- LLM: any of Groq / Gemini / OpenAI / Claude / Ollama, auto-detected from runtime overrides → env vars.

**Carry-over for future sessions:**
- The cross-episode `POST /api/run` contract is still locked. New episodes should also expose `POST /api/chat` (richer interface) if they want the freeform chat UX out of the box.
- `intent.py` and `safety.py` are framework-agnostic — they transfer directly to LangGraph / ADK / AutoGen episodes.
- The fast classifier's regex set is English + Tamil/Tanglish; future non-Indian-language episodes should extend it (or rely more heavily on the LLM fallback).

---

## Template for a new episode

Copy this block when adding an episode:

```markdown
## EP## — <Name>

| | |
|---|---|
| **Framework** | <e.g. LangGraph 0.x> |
| **Problem** | <one-line description> |
| **LLM** | <BYOK / specific provider / local> |
| **Tools** | <list> |
| **Observability** | <OpenLIT / Langfuse / none> |
| **Folder** | `<folder_name>/` |
| **Status** | 🔴 Planned / 🟡 In progress / 🟢 Shipped |
| **Contract** | ✅ Matches API_CONTRACT.md / ❌ Pre-contract |

**Architecture highlights:**
- ...

**What worked:** ...

**What didn't (and why):** ...

**Test results:**
- **<low-extreme city>** (AQI ?, "<level>"): ...
- **<high-extreme city>** (AQI ?, "<level>"): ...

**Lessons for future episodes:** ...
```

---

## Rough roadmap

| # | Tentative framework | Tentative problem |
|---|---|---|
| EP02 | LangGraph | TBD — graph-structured planning agent? |
| EP03 | Google ADK | TBD |
| EP04 | AutoGen | TBD — conversational multi-agent? |
| EP05 | DSPy | TBD — declarative + optimised prompts? |

Each future episode plugs into the same `agentverse-frontend/` by complying with `API_CONTRACT.md`. The problem domain can stay weather/AQI/meme (so they're directly comparable) or vary per episode — that's an editorial choice for the series.

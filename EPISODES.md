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

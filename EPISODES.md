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
- Always run a high-extreme and low-extreme test (e.g. Chennai vs Delhi) to verify the creative agent isn't stuck on one tone
- ContextVar side-channel pattern transfers to any framework where you control the tool layer
- Free-tier LLM (Groq) is plenty fast for a 3-agent sequential crew (~10-20s end-to-end)

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

# Voice Agent Providers — Deep Comparison (for "Claude Code in the car")

> Companion to `voice-claude-code-plan.md`. Scope: managed/framework platforms that orchestrate STT + TTS + turn-taking and let us **bring our own LLM** (so Claude Code is the brain). Evaluated for one specific job: a personal, on-demand, hands-free Claude Code copilot reached from a car, with the brain on a remote headless server.
>
> Prices are 2026 ballparks — **verify current rates before committing.** All figures exclude Anthropic token costs, which are paid directly to Anthropic and are common to every option.

---

## TL;DR

- **Best voice + fastest to a working demo → ElevenLabs Agents** (our chosen v0).
- **Cheapest for personal volume → LiveKit Cloud** — its free Build tier (1,000 agent-min/mo) covers our ~440 min/mo for **$0** orchestration. (Caveats for a UK user: the free inbound number is **US-only** — rent a UK number or go app/WebRTC instead; and its first-party `anthropic` plugin wraps the Claude *API*, not Claude *Code*, so we build the custom node either way. See the contract note below.)
- **Region (UK):** we're UK-based — run everything in an **EU/UK region** (ElevenLabs EU residency endpoint, LiveKit/Twilio EU regions, brain server in London). Transatlantic hops add ~100–150 ms each across a multi-hop voice turn and dominate the experience. Use a **UK phone number** (free to call from a UK mobile plan), never a US one.
- **Simplest telephony → Twilio ConversationRelay** (it *is* Twilio; no separate phone wiring).
- **Most control / portability → Pipecat** (self-host the framework for free, or its managed Cloud).
- The adapter's *core* (Claude Agent SDK session + filler/keepalive) is reused everywhere, but the *outer shell* differs per platform — see §"Integration contract" below.

## The dimension that actually decides the work: integration contract

How each platform expects to call "your LLM" determines what we build. Four shapes:

| Shape | Platforms | What we build |
|-------|-----------|---------------|
| **OpenAI-compatible HTTP + SSE** (`/v1/chat/completions`, `data: {…}` chunks) | **ElevenLabs**, **Vapi** | A FastAPI service that looks like OpenAI, drives Claude Agent SDK inside. (This is the `voice-claude-code-plan.md` §5 adapter.) |
| **WebSocket, text-in/text-out** (platform does STT/TTS; you exchange plain JSON text messages) | **Twilio ConversationRelay**, **Retell** (custom-LLM WS) | A WebSocket server: receive transcript message → run Claude → stream text frames back. *Simpler* than OpenAI shape — no SSE/envelope mimicry. |
| **BYO-provider URL + headers** (expects the real Anthropic **Messages API** shape) | **Deepgram Voice Agent** | Wrap Claude Code behind an Anthropic-Messages-compatible endpoint. *More* work (must emulate Messages API streaming), unless you point it at plain Claude and lose the agent. |
| **In-process plugin / pipeline node** (you write the agent in their framework) | **LiveKit Agents**, **Pipecat** | A custom LLM node/processor that calls the Claude Agent SDK in-process. Most flexible; no public HTTP endpoint to secure. |

**Implication:** the reusable kernel is "Claude Agent SDK session keyed by conversation + filler while it thinks." The shell (OpenAI SSE / WS text / Anthropic-shape / plugin) is a thin swap. So the v0 choice is reversible, but "build once, run anywhere" is ~80% true, not 100%.

> Note on LiveKit/Pipecat's native **Anthropic plugin**: it wires the Claude *API* (a fast chat model), **not** Claude *Code* (agentic, tools, your repo). To get real Claude Code we still wrap the **Agent SDK** as a custom LLM node — the native plugin is a nice fallback for plain chat, not a substitute.

## The problem common to ALL of them

Every platform assumes a **fast, stateless, turn-based chat LLM**. Claude Code is **slow, stateful, agentic** (tool runs of 10–60s). So on *every* option we must:
1. keep our own durable Claude session (don't replay history each turn), and
2. stream filler/progress immediately so turn-taking doesn't time out and the line never goes dead.

The **framework options (LiveKit, Pipecat)** give the most control to handle long turns gracefully (we own the pipeline and timeouts). The **managed options** impose turn-taking behavior we must work *around* with filler. This is the single biggest product risk and it doesn't disappear by picking a different vendor.

---

## Per-provider deep dive

### ElevenLabs Agents — *chosen v0*
- **LLM:** OpenAI-compatible custom LLM (`/v1/chat/completions` or `/v1/responses`, SSE). Easy Claude wrap.
- **Telephony:** Twilio/SIP — **not bundled** (wire Twilio/Vonage ~$0.013–0.026/min/leg).
- **Voice:** best-in-class TTS (Flash v2.5, ~75ms first audio), 5k+ voices, 70+ langs.
- **Latency / turn-taking:** proprietary turn-taking model; strong barge-in.
- **Price:** ~$0.08–0.10/min orchestration (bundled-minutes since Nov 2025; 95% discount for silence >10s; burst $0.16/min).
- **Free tier:** trial credits only; no ongoing free tier.
- **Lock-in:** moderate (managed), but OpenAI-shaped LLM keeps the adapter portable.
- **Best for:** fastest, best-sounding demo. **Weakness:** priciest per-minute; telephony not included.

### LiveKit Agents / LiveKit Cloud — *cost winner for personal use*
- **LLM:** plugin system; **native Anthropic plugin** for chat-Claude, **custom LLM node** for Claude Code agentic. WebRTC-native.
- **Telephony:** SIP 1.0 (inbound/outbound, DTMF, warm/cold transfer). **Free inbound US number on the Build tier.**
- **Voice:** any provider via plugins (ElevenLabs/Cartesia/Deepgram/…), or LiveKit Inference.
- **Latency:** WebRTC-native, very low; multi-participant rooms.
- **Price:** **Build plan FREE — 1,000 agent-session min/mo + Inference credits + 1 free phone number.** Beyond: ~$0.01/min agent + telephony $0.005–0.015/min. Open source (Apache 2.0), self-hostable.
- **Lock-in:** low (OSS core, portable).
- **Best for:** **cheapest at our volume (≈free), best client SDKs (Swift for the later CallKit app).** **Weakness:** you write the agent code; more moving parts than ElevenLabs.

### Twilio ConversationRelay — *simplest telephony*
- **LLM:** BYO via **WebSocket** — Twilio sends transcribed text, you stream text back; Twilio does STT/TTS + interruption (`interruptible` attr).
- **Telephony:** **native — it is Twilio.** No separate provider to wire.
- **Voice:** choice of best-of-breed TTS providers/voices via console.
- **Price:** ~$0.07/min for ConversationRelay + standard Twilio voice; BYO LLM separate. (Verify.)
- **Free tier:** Twilio trial credit; no ongoing free agent tier.
- **Lock-in:** Twilio account + their WS protocol (but the WS-text shell is simple to re-target).
- **Best for:** "call a number from the car" with zero telephony glue. **Weakness:** WS protocol is Twilio-specific; voice quality good but not ElevenLabs-tier.

### Vapi — *max LLM control*
- **LLM:** any OpenAI-compatible endpoint (streaming); auth via `/credential` (API key/OAuth2). Per-stage LLM swap, "Squads" (multi-agent in one call).
- **Telephony:** built-in.
- **Price:** $0.05/min orchestration **+ pass-through provider costs (no markup on providers)** → real-world $0.07–0.25/min. $10 trial credits, no ongoing free tier.
- **Latency:** ~500–800ms typical.
- **Lock-in:** moderate; OpenAI-shaped LLM keeps adapter portable.
- **Best for:** complex multi-agent call flows. **Weakness:** orchestration markup compounds; overkill for a personal single-agent copilot.

### Retell AI — *balanced, compliance-friendly*
- **LLM:** no provider limits; BYO via **WebSocket custom-LLM** (official node demo). Also offers bundled Claude 4.5 Sonnet (~$0.08/min) if you don't BYO.
- **Telephony:** built-in.
- **Price:** **$0.07/min base voice engine** (STT+latency mgmt+TTS), no platform fees/bundles. $10 free credits (~60 min).
- **Latency:** ~580–620ms (consistent).
- **Lock-in:** moderate; WS shell re-targetable; strong HIPAA/PHI story.
- **Best for:** predictable flat per-minute, compliance. **Weakness:** WS contract is Retell-specific; voice not ElevenLabs-tier.

### Pipecat (OSS framework) / Pipecat Cloud — *most control + portability*
- **LLM:** 80+ providers incl. Anthropic; for Claude Code, a custom processor wrapping the Agent SDK.
- **Telephony:** integrated SIP ($0.005/min) + PSTN ($0.018/min) + transfers ($0.20/event) on Cloud; or wire your own when self-hosting.
- **Voice:** any (Cartesia/Deepgram/ElevenLabs/…).
- **Price:** **OSS framework free to self-host**; Cloud agent hosting $0.01–0.03/min. Krisp noise suppression free <10k min/mo.
- **Lock-in:** lowest (vendor-neutral OSS). HIPAA/GDPR.
- **Best for:** owning every layer, cheapest self-host. **Weakness:** you build & operate the pipeline; most engineering of the lot.

### Deepgram Voice Agent API — *single-vendor, BYO LLM*
- **LLM:** BYO by setting provider type (Anthropic) + your endpoint URL + headers (expects Anthropic-shape); built-in function calling, barge-in, turn-taking; provider fallback chains.
- **Telephony:** none native — bridge via Twilio.
- **Voice:** Deepgram Aura TTS / Deepgram STT (no ElevenLabs voices).
- **Price:** flat **$4.50/hr** full stack (~$0.075/min), cheaper with BYO model (BYOM reductions).
- **Lock-in:** Deepgram STT/TTS; Anthropic-shape LLM contract is the most bespoke to emulate for Claude Code.
- **Best for:** one bill, tight Deepgram latency. **Weakness:** no native telephony; Anthropic-Messages emulation is the hardest shell.

---

## Cost at our volume (~440 min/mo = ~20 min/day × 22 days, on-demand)

Orchestration/voice only; **Claude tokens extra everywhere**; telephony noted.

| Provider | Orchestration/voice + telephony @ 440 min/mo | Notes |
|----------|----------------------------------------------|-------|
| **LiveKit Cloud** | **~$0** | Inside free Build tier (1,000 min) + free inbound number. **Standout.** |
| **Pipecat (self-host OSS)** | **~$8** (just PSTN/Twilio) | Framework free; you run it. |
| **Pipecat Cloud** | ~$13–22 | $0.01–0.03/min hosting + PSTN $0.018 + STT/TTS. |
| **Vapi** | ~$22 + provider STT/TTS + telephony | $0.05/min orchestration + pass-through. |
| **Twilio ConversationRelay** | ~$31–35 | ~$0.07/min incl. telephony + STT/TTS. |
| **Retell** | ~$31 + telephony | $0.07/min base. |
| **Deepgram Voice Agent** | ~$33 + Twilio bridge | $4.50/hr full stack. |
| **ElevenLabs Agents** | ~$44 + ~$6 Twilio = **~$50** | Best voice; priciest. (≈$30 effective with silence discount.) |

At personal scale the spread is **$0 → ~$50/mo** for the *voice* layer — and **Claude tokens likely dominate** the bill on every row, which is why model routing (Sonnet for steering, Opus for grinding) matters more than vendor choice.

## Recommendation

1. **v0 (now): ElevenLabs Agents** — as decided. Best voice, 15–30 min to stand up, OpenAI-shaped adapter (the portable kernel). Accept the higher per-minute to validate the experience fast.
2. **Cost path (when the bill matters): LiveKit Cloud** — free at our volume, free inbound number, low-latency WebRTC, and the best Swift SDK for the eventual CallKit/CarPlay app. (Its `anthropic` plugin is Claude-the-*API*, not Claude Code — we wrap the Agent SDK as a custom LLM node regardless.) Migrating means swapping the adapter's *shell* (OpenAI-SSE → LiveKit custom-LLM node); the Claude-session kernel is unchanged.
3. **Telephony-simple fallback: Twilio ConversationRelay** — if wiring Twilio under ElevenLabs proves annoying, ConversationRelay collapses telephony + STT/TTS into one Twilio bill with a dead-simple WS-text contract.
4. **Self-host endgame: Pipecat OSS** — if you want near-zero marginal cost and full control once the design is proven.

**Decision driver:** pick by *integration contract* and *free-tier fit*, not by raw per-minute — because the adapter kernel is shared and Anthropic tokens are the real cost. ElevenLabs to learn fast; LiveKit to run cheap.

## Sources
- ElevenLabs Agents: <https://elevenlabs.io/docs/agents-platform>, <https://elevenlabs.io/pricing/agents>
- LiveKit: <https://docs.livekit.io/agents/>, Anthropic plugin <https://docs.livekit.io/agents/models/llm/anthropic/>, pricing <https://livekit.com/pricing>
- Twilio ConversationRelay: <https://www.twilio.com/docs/voice/conversationrelay>
- Vapi custom LLM: <https://docs.vapi.ai/customization/custom-llm/using-your-server>
- Retell integrate LLM: <https://docs.retellai.com/integrate-llm/integrate-llm>, demo <https://github.com/RetellAI/retell-custom-llm-node-demo>
- Pipecat Cloud: <https://www.daily.co/pricing/pipecat-cloud/>, framework <https://github.com/pipecat-ai/pipecat>
- Deepgram Voice Agent: <https://deepgram.com/product/voice-agent-api>, LLM models <https://developers.deepgram.com/docs/voice-agent-llm-models>

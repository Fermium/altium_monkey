# Voice Claude Code — Design & Build Plan ("Claude Code in the car")

> Status: design / planning. Chosen path for v0: **ElevenLabs Agents Platform with Claude as a custom (bring-your-own) LLM, reached by phone, used on-demand.**
> Author context: we want to talk to Claude Code while driving, with Claude Code running on a **remote, headless server** (no local audio hardware).

---

## 1. Goal & constraints

- **Goal:** use Claude Code hands-free during a commute (≈ two 1-hour drives/day). Stretch goal: a proper CarPlay experience.
- **Hard constraint:** Claude Code runs on a **remote server with no microphone or speakers**. The audio must originate wherever the human is (the car/phone), not where the brain runs.
- **Soft goals:** small/clean surface area, modern streaming voice, low recurring cost, no dependence on Apple App Store approval to get started.

## 2. Why the existing tool (VoiceMode) doesn't fit

[VoiceMode](https://github.com/mbailey/voicemode) is an MCP server that records and plays audio **inside its own process** (`record_audio()` via PortAudio/sounddevice). It assumes the machine running Claude Code *is* the machine with the mic and speakers — your laptop. On a headless remote server there is no audio device, so it cannot work. It also carries a large surface area (DJ module, soundfonts, a multi-agent "conch" mutex) that we don't need.

The single fatal assumption: **audio I/O is local to the brain.** Everything below is built on breaking that assumption.

## 3. Core architectural principle

Separate the three things VoiceMode fused onto one box:

| Layer | Responsibility | Where it must live |
|-------|----------------|--------------------|
| **Audio edge** | mic + speaker | where the human is (car / phone) |
| **Brain** | Claude Code (reads repo, runs tools, edits code) | the remote server |
| **Voice models** | STT + TTS + turn-taking | anywhere; ideally a managed streaming service |

The mental-model flip vs. VoiceMode:

- **VoiceMode:** Claude Code is the *driver*; voice is a tool it calls.
- **This design:** the voice platform is the *driver*; it calls **Claude as its reasoning node.**

For hands-free use the inversion is an advantage — the hard real-time work (VAD, barge-in, turn-taking, telephony) is owned by the platform, and Claude just has to be a well-behaved streaming endpoint.

## 4. Chosen architecture (v0): ElevenLabs Agents + Claude custom LLM + phone

```
  ┌───────────┐   PSTN call    ┌──────────────────────────────┐   HTTPS/SSE   ┌────────────────────────┐
  │  Car /    │  (Bluetooth     │   ElevenLabs Agents Platform │  OpenAI-       │  Our Adapter (server)  │
  │  iPhone   │◄──hands-free──►│   STT → [LLM] → TTS →         │  compatible    │  FastAPI  ⇄            │
  │  (audio   │                 │   turn-taking / barge-in     │◄─custom-LLM───►│  Claude Agent SDK      │
  │   edge)   │                 │   + native Twilio/SIP        │   endpoint     │  (headless Claude Code)│
  └───────────┘                 └──────────────────────────────┘                └────────────────────────┘
```

ElevenLabs owns STT, TTS, turn-taking/interruption, and the telephony bridge. The **only thing we build** is a small HTTP service (the "Adapter") that looks like an OpenAI chat-completions endpoint on the outside and drives a headless Claude Code session on the inside.

Why ElevenLabs for the "fancy" v0:
- Best-in-class TTS (Flash v2.5, ~75 ms first audio) — you'll be listening for hours, voice quality matters.
- Genuinely quick to stand up (basic agent in 15–30 min if you already have an LLM endpoint).
- Native Twilio + SIP telephony → the car works **today, with no app and no Apple approval**.
- The custom-LLM contract is a plain OpenAI-compatible endpoint → **portable** to competitors (see §10).

## 5. The custom-LLM adapter (the only thing we build)

### 5.1 The contract ElevenLabs expects

ElevenLabs calls **our** server as if it were OpenAI:

- Endpoint: OpenAI-compatible **`POST /v1/chat/completions`** (Chat Completions) — or `/v1/responses` (Responses API). Use Chat Completions; it's simpler.
- Must stream **Server-Sent Events** (`Content-Type: text/event-stream`): `data: {chunk}\n\n` … terminated by `data: [DONE]\n\n`.
- Request fields sent by ElevenLabs: `messages` (full role/content history), `model`, `temperature`, `max_tokens`, `stream: true`, `user_id`, `tools` (ElevenLabs *system* tools), and `elevenlabs_extra_body` (pass-through custom params).
- Tool calls are exchanged in standard OpenAI function-calling format.
- Config in the ElevenLabs dashboard: agent → **Custom LLM** → server URL + Model ID → store a secret named `OPENAI_API_KEY` (acts as the bearer the platform sends us) → publish. Use a tunnel (ngrok) for local dev; the real server's HTTPS endpoint in prod.

### 5.2 What the adapter does internally

Wrap the **Claude Agent SDK** (`claude-agent-sdk` for Python / `@anthropic-ai/claude-agent-sdk` for TS) — the same agent loop, tools, and context management that power Claude Code, run headless.

1. **Receive** the OpenAI request. Take the last user message as the new turn; ignore replaying the rest (we keep state ourselves — see next).
2. **Map to a persistent Claude session.** Key a Claude Agent SDK `session_id` by ElevenLabs `user_id`/conversation id. First turn: start a session, capture `session_id` from the init message. Subsequent turns: `resume` that session so repo/context/tool state persists across turns (and across adapter restarts).
3. **Run Claude's agent loop** with `include_partial_messages` (Python) / `includePartialMessages` (TS) so we get incremental assistant text and tool events as they arrive.
4. **Stream Claude's assistant text back** as OpenAI SSE chunks, so ElevenLabs' TTS speaks it as it's generated.
5. **Permissions:** run headless with a pre-approved `allowed_tools` allowlist and a non-interactive permission mode + a `can_use_tool` callback that auto-decides — the loop must never block waiting for a human while you're driving.

### 5.3 The one genuinely hard problem: stateless-fast vs. stateful-slow

ElevenLabs' custom-LLM contract assumes a **stateless, turn-based, fast** chat model. Claude Code is **stateful, agentic, and slow** — it may run tools for 10–60 s before it has anything to say. Bridging that is the real engineering:

- **Keepalive / filler.** The moment a turn starts, immediately stream a short spoken acknowledgement ("let me take a look…") and narrate progress while Claude works, so the line never goes dead and turn-taking doesn't time out. Never let the SSE stream stall silently.
- **Session mapping** (above) replaces ElevenLabs' resend-the-whole-history model with our own durable Claude session.
- **Tool placement.** Keep the *code/agentic* tools **inside** the Claude session (that's where the repo and file tools live). Let ElevenLabs own only *conversation-control* system tools (end call, transfer, language switch). Do **not** expose the codebase as ElevenLabs tools.

### 5.4 Adapter sketch (Python / FastAPI — illustrative)

```python
# POST /v1/chat/completions  — OpenAI-compatible SSE, backed by Claude Agent SDK
@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest, authorization: str = Header(...)):
    assert authorization == f"Bearer {EXPECTED_SECRET}"          # the ElevenLabs OPENAI_API_KEY secret
    user_text = req.messages[-1].content
    convo_id  = req.user_id or "default"
    session   = sessions.get(convo_id)                            # our durable map → Claude session_id

    async def event_stream():
        yield sse_delta("One sec, let me look…")                  # 5.3 filler: speak immediately
        async for ev in claude.query(                             # claude-agent-sdk, streaming
                prompt=user_text,
                options=Options(resume=session, include_partial_messages=True,
                                allowed_tools=ALLOWLIST, permission_mode="acceptEdits",
                                can_use_tool=auto_decide)):
            if ev.type == "system" and ev.subtype == "init":
                sessions[convo_id] = ev.session_id               # persist session for next turn
            elif ev.type == "assistant_text_delta":
                yield sse_delta(ev.text)                          # stream Claude's words → TTS
            # (optionally narrate tool activity here as more filler)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

(`sse_delta` wraps text in the OpenAI `chat.completion.chunk` shape. Names are illustrative — confirm exact SDK event types against the Agent SDK docs when implementing.)

## 6. Telephony & the car

- **v0 — phone number (no app, no Apple approval).** ElevenLabs has native Twilio + SIP. Assign a number to the agent; call it from the car over Bluetooth hands-free. This is the fastest route to the actual goal. (Telephony billed separately, ~$0.01–0.026/min/leg via Twilio/Vonage.)
- **v1 — CallKit iOS app (better audio, still no approval).** A normal iOS app that models the session as a **CallKit VoIP call** surfaces as the native in-car call UI and routes audio through the car — **CallKit needs no CarPlay entitlement**. Build it, sideload to your own iPhone with a paid dev account ($99/yr), done. Connect it to the agent via ElevenLabs' Swift/WebRTC SDK for HD audio instead of 8 kHz telephony.
- **v2 — true CarPlay UI (optional).** iOS 26.4 (Feb 2026) added a CarPlay entitlement category for **"voice-based conversational apps"** — the first official third-party slot. Only needed if you want an on-screen transcript/buttons; requires Apple to grant the entitlement (a request form, separate from App Store review).

## 7. On-demand UX (the main cost lever)

**Do not keep an open line for the whole commute.** Design for **push-to-talk / wake-word / on-demand calls** from day one. You then pay for minutes of *actual conversation* (~15–20 min of a 60-min drive), not idle time. This single decision cuts ~80% of voice cost regardless of vendor, and it's the difference between "pricey" and "cheap" below.

## 8. Cost model

Assume ~22 commute-days/month, 2 hrs/day of drive time.

| Setup | Voice cost/mo (Anthropic tokens always extra) |
|-------|----------------------------------------------|
| ElevenLabs, line open whole commute | ~$264 (≈$110 with the 95% silence discount) |
| **ElevenLabs, on-demand (~20 min/day)** | **~$44** + Twilio ~$4 |
| Self-host (Pipecat + Deepgram STT/TTS + Twilio), on-demand | ~$10–15 |
| Self-host local (Whisper.cpp + Kokoro + Twilio), on-demand | ~$4 (basically just telephony) |

Notes:
- ElevenLabs Agents: **~$0.08–0.10/min**, billed on a bundled-minutes model since Nov 2025; **95% discount for silence >10 s** (helps a "thinking" coding agent a lot); burst **$0.16/min** over the concurrency limit. **Telephony is not included** — wire Twilio/Vonage separately.
- **LLM tokens pass through separately** — with a custom LLM you pay **Anthropic directly** for Claude. This may be your *dominant* cost during heavy agentic work. Mitigation: run the in-car conversational steering on **Sonnet**, reserve **Opus** for the genuinely hard grinding.
- Component ballparks (verify current rates): Deepgram streaming STT ~$0.004/min; Twilio inbound ~$0.0085/min; local Whisper+Kokoro = $0 for the models.

## 9. Competitor landscape & why ElevenLabs now

Every serious managed platform supports a **bring-your-own / OpenAI-compatible custom LLM** and telephony. That's the crucial fact: **our adapter is portable**, so the v0 choice is reversible.

| Platform | BYO LLM | Telephony | ~Price (voice/orchestration) | Notes |
|----------|---------|-----------|------------------------------|-------|
| **ElevenLabs Agents** | ✅ OpenAI-compatible | Twilio/SIP (not bundled) | ~$0.08–0.10/min | **Best voice**, fastest setup. Our pick for v0. |
| **Vapi** | ✅ swap per stage, "Squads" | Built-in | $0.05/min orchestration **+ marked-up components** | Max LLM control; gets expensive at scale. |
| **Retell AI** | ✅ modular | Built-in | $0.07/min base; $0.13–0.31 all-in | Compliance-friendly (PHI), cheapest TCO at high volume. |
| **Twilio ConversationRelay** | ✅ | **Native (it *is* Twilio)** | ~$0.07/min | Telephony included; strong fallback for the car. |
| **Pipecat Cloud** | ✅ | SIP $0.005 / PSTN $0.018 | $0.01–0.03/min hosting | Managed Pipecat; cheap, more control. |
| **LiveKit Cloud Agents** | ✅ | SIP/PSTN | **$0.01/min, free ≤1K min/mo** | Cheapest orchestration; **free tier covers personal on-demand use**. |

Takeaways:
- **For best voice + fastest demo → ElevenLabs** (v0, now).
- **For cheapest at our personal volume → LiveKit Cloud** (free up to 1K min/mo ≈ our ~440 min/mo on-demand) — strong cost fallback.
- **For telephony-included simplicity → Twilio ConversationRelay.**
- Because all four speak OpenAI-compatible BYO-LLM, **the adapter from §5 is built once and works against any of them.**

## 10. Build phases

- **Phase 0 — Adapter spike (local).** FastAPI `/v1/chat/completions` SSE endpoint wrapping the Claude Agent SDK; verify against a local OpenAI-compatible test client. Get streaming + session resume + the filler/keepalive working. *Deliverable: text-in/text-out Claude over an OpenAI endpoint.*
- **Phase 1 — ElevenLabs wiring.** Expose the adapter (ngrok → then a real HTTPS endpoint on the server), point an ElevenLabs agent at it as Custom LLM, talk to it from the browser SDK. *Deliverable: voice conversation with Claude Code from a laptop.*
- **Phase 2 — The car (phone).** Attach a Twilio number to the agent; design **on-demand** (push-to-talk / wake) rather than open-line; tune turn-taking/interruption + filler latency for driving. *Deliverable: call a number from the car and steer Claude Code.*
- **Phase 3 — Polish / cost.** Sonnet-vs-Opus routing, token/minute telemetry, prompt for brevity, persona/voice. Evaluate migrating orchestration to LiveKit Cloud if cost climbs (adapter unchanged).
- **Phase 4 (optional) — CallKit app**, then a CarPlay app via the iOS 26.4 voice category, for HD audio and an on-screen UI.

## 11. Risks & open questions

- **Latency of a slow agent over a voice line.** The filler/keepalive strategy (§5.3) is unproven for 30–60 s tool runs; needs real tuning. Biggest product risk.
- **Anthropic token spend** may dominate cost; measure early, route models accordingly.
- **Security:** the adapter is a public HTTPS endpoint that drives an agent with file/tool access. Lock it down — bearer-secret check, tight `allowed_tools`, non-interactive permissions, and ideally network/IP allowlisting to ElevenLabs. Treat anything spoken as untrusted input to the agent.
- **Driving safety / distraction** — keep it voice-first, minimal screen interaction.
- **Exact Agent SDK event names / options** in §5.4 are illustrative — confirm against current SDK docs at build time.

## 12. References

- VoiceMode source: <https://github.com/mbailey/voicemode> (PyPI `voice-mode`)
- ElevenLabs Agents — overview, custom LLM, telephony, pricing: <https://elevenlabs.io/docs/agents-platform>, <https://elevenlabs.io/pricing/agents>
- Claude Agent SDK (headless / streaming / sessions): <https://code.claude.com/docs/en/headless>, <https://platform.claude.com/docs/en/agent-sdk/overview>
- Competitors: Vapi, Retell AI, Twilio ConversationRelay, Pipecat Cloud, LiveKit Cloud Agents
- CarPlay / CallKit / iOS 26.4 voice-conversational category: Apple CarPlay developer docs; MacRumors/AppleInsider coverage (Feb 2026)

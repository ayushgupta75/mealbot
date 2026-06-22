# Backlog

Planned work, not yet built. Keep entries actionable enough to pick up cold.

## Voice-call ordering (Vapi + Twilio)

Turn the local mic/speaker voice mode into a real phone-call agent. The LangGraph
brain (intake/fulfillment agents, cart, menu lookups, validation, ordering backend)
ports unchanged; this is an I/O-edge + deployment change. See `PROJECT_GUIDE.md` §12
for the full design.

**Approach:** Vapi for the voice layer (telephony via a Twilio number, streaming
STT/TTS, turn-taking) with our graph behind a FastAPI **Custom LLM** endpoint.

**Tasks:**
- [ ] FastAPI server exposing an OpenAI-compatible `/chat/completions` endpoint (what
      Vapi's Custom LLM calls each turn).
- [ ] Adapter: translate Vapi's OpenAI-shaped request ↔ LangGraph graph invoke;
      stream the reply back as SSE so Vapi can start speaking sooner.
- [ ] Map Vapi call ID → LangGraph `thread_id` so each caller gets isolated state.
- [ ] Swap `MemorySaver` for a persistent checkpointer (SQLite/Postgres) so call state
      survives across the call and process restarts.
- [ ] Provision: Vapi assistant config + a Twilio number bridged to Vapi.
- [ ] Tests for the endpoint/adapter (offline, same style as the rest).

**Open questions:**
- Keep tool-calling inside the graph (preferred) vs. expose some as Vapi functions?
- Latency budget — confirm streaming end-to-end stays under ~800ms round-trip.

**Alternative (more control, no Vapi):** Twilio Media Streams → Deepgram (streaming
STT) → graph → ElevenLabs (streaming TTS), orchestrated with Pipecat or LiveKit.

## Other known items

From `PROJECT_GUIDE.md` §13:
- [ ] Per-user `thread_id` (today it's hard-coded to one session).
- [ ] Customer identity for reorder (today "last order" is global, not per-customer).
- [ ] Payment + real fulfillment/kitchen integration.
- [ ] Structured logging + latency metrics before production.

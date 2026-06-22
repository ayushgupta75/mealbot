# Mealbot — Project Guide & Interview Reference

A complete, plain-English walkthrough of how this project works: what it does, how
it's built, the design decisions and *why* they were made, how it's tested, and how
it would become a real phone-call agent with Vapi + Twilio. Read this end-to-end and
you should be able to answer essentially any question about the project.

---

## 1. One-paragraph summary

Mealbot is a conversational food-ordering assistant. A customer orders in plain
language (typed, or spoken in voice mode); the assistant answers menu questions,
builds and edits an order with the customer, reads it back, and places it once they
confirm. Under the hood it's a **multi-agent system built on LangGraph**, driven by
**Claude** (`claude-sonnet-4-6`). The interesting engineering is the split between
what the **language model decides** (the conversation) and what the **code
guarantees** (prices, totals, validation, persistence) — that boundary is what keeps
orders correct even when the model gets creative.

---

## 2. What it does (features)

- **Natural-language ordering** — the customer just says what they want.
- **Menu Q&A and dietary filters** — "what's vegan?", "anything under $5?",
  "what's gluten-free / not spicy?" — answered from menu data, not the model's memory.
- **Live cart** — add items, change quantity or spice level, or remove items at any
  point before confirming, with a running total.
- **Reorder** — "the usual" / "same as last time" pulls up the previous order.
- **Confirmation** — always reads the full order back before placing.
- **Validation** — prices and totals are checked against the menu before an order can
  be placed.
- **Persistence & dispatch** — every placed order is saved to a local SQLite history
  and, optionally, POSTed to an external webhook.
- **Voice mode** — speak the order; the assistant talks back and you can interrupt it.

---

## 3. Tech stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11+ | — |
| Agent framework | LangGraph (`StateGraph`, `create_react_agent`, `MemorySaver`) | State machine + tool-calling agents with memory |
| LLM | Claude `claude-sonnet-4-6` via `langchain-anthropic` | The conversational brain |
| Tools | LangChain core tools, `InjectedState` | Typed, state-aware tools |
| Order history | SQLite (`sqlite3`, stdlib) | Persistence + reorder, zero-dependency |
| Webhook dispatch | `urllib` (stdlib) | Outbound order delivery with timeout + retry |
| Speech-to-text | mlx-whisper (Apple Silicon) | On-device transcription (today) |
| Text-to-speech | macOS `say` | Spoken responses + barge-in |
| Audio I/O | sounddevice, numpy | Mic capture |
| Tests | pytest | 50+ offline tests |

---

## 4. The big picture

The whole app is a **graph with two nodes**. A turn flows left to right:

```
                 ┌─────────────────────────────────────────────┐
   user input →  │  OUTER GRAPH (agent.py, a StateGraph)        │
                 │                                              │
                 │   START → [ intake ] ──(order set?)──┐       │
                 │                │ no                   │ yes   │
                 │                ↓                      ↓       │
                 │               END               [ fulfillment ] → END
                 └─────────────────────────────────────────────┘
                          ↑                              ↓
                  shared State: messages, cart, order   prints / saves / dispatches
```

- **intake** is a tool-calling agent that runs the conversation and builds the order.
- **fulfillment** is a second agent that places the confirmed order.
- They communicate through **shared graph state** (`messages`, `cart`, `order`), and
  the routing decision between them is "has an order been confirmed yet?"

The whole graph is compiled with a `MemorySaver` checkpointer and a fixed
`thread_id`, so the conversation, cart, and order **persist across turns** within a
run. Each user message is one `graph.invoke(...)`.

---

## 5. The core mental model: who decides what

This is the single most important idea in the project, and the best thing to lead
with in an interview.

> **The LLM runs the conversation. The code owns anything that has to be correct.**

- The model decides *what to say*, *which tool to call*, and *when the order is done*.
- The **code** owns prices (looked up from the menu, never taken from the model), the
  **running total** (summed in Python), **validation** (every order re-checked against
  the menu), and **persistence**.

So if the model hallucinates a price, invents an off-menu item, or fumbles arithmetic,
it physically cannot push a wrong order through — the deterministic layer rejects it.
This is the answer to "how do you make an LLM app reliable?": you don't trust the LLM
with the parts that must be right.

---

## 6. Component-by-component walkthrough

### `mealbot.py` — entry point
A REPL loop. `make_io(voice)` returns `get_input` / `send_output` functions that
abstract away text vs. voice, so the main loop doesn't care which mode it's in. Each
iteration reads one user message, calls `graph.invoke(...)`, prints the reply, and
breaks once `intake_complete()` reports the order is placed.

### `agent.py` — the outer graph
`build_graph()` wires the `StateGraph`: `START → intake`, a conditional edge
(`route_after_intake`), and `fulfillment → END`. `route_after_intake` is a one-liner:
return `"fulfillment"` if `state["order"]` is set, else `END`. Compiled with
`MemorySaver` and `thread_id="session-1"`.

### `state.py` — shared state
A `State` TypedDict with three channels:
- `messages` — full history, merged with the `add_messages` reducer (append semantics).
- `cart` — the in-progress line items; replaced wholesale on each edit (last-write-wins).
- `order` — the snapshot taken at confirmation; **its presence is the routing signal**.

### `menu.json` + `menu.py` — the menu is data
The menu lives in `menu.json` as `{name, price, tags}`. Tags carry dietary info
(`veg`, `vegan`, `contains-dairy`, `contains-gluten`, `mild`) plus a category.
`menu.py` loads it once and is the **single source of truth** consumed by three
places: the intake prompt (`format_menu_for_prompt`), the menu-query tool, and the
voice transcription hint (`menu_item_names`). Change the menu in one file, everything
updates.

### `intake_agent.py` — the conversation agent
A `create_react_agent` with seven tools: `query_menu`, `fetch_last_order`, the four
cart tools, and `save_order_details_to_graph`. Two non-obvious things:
- Its state schema is **`IntakeState`** (`AgentState` extended with `cart` and
  `order`), so the cart is in scope for the tools and round-trips to the outer graph.
- The model is bound with **`parallel_tool_calls=False`** (see §8.3 — this fixed a
  real bug).

`intake_complete(result)` simply returns whether `result["order"]` is set.

### `menu_query.py` — `query_menu` tool
Stateless. Filters `menu.json` by dietary tags and/or `max_price`, AND-combining the
filters. `"mild"` answers "what's not spicy?"; `"dairy-free"` / `"gluten-free"` are
negations of the `contains-*` tags. Returns matching items, or an error string for an
unknown filter (so the model gets clear feedback instead of silent wrong answers).

### `cart.py` — the cart tools
`add_to_cart`, `update_cart_item`, `remove_from_cart`, `view_cart`. They **read** the
current cart via `InjectedState` and **write** it back by returning a `Command` that
replaces the `cart` channel. Key points:
- **Prices come from the menu here**, not from the model.
- `cart_total` computes the running total in Python.
- Each tool **validates** (on-menu, positive integer quantity, spice 1–5) and returns
  a plain rejection message on bad input, leaving the cart untouched.
- Adding the same item + spice level **merges** into the existing line (quantity +=).

### `save_order_details_to_graph.py` — confirmation / handoff
Reads the cart from `InjectedState` and **snapshots it** into `order` (so the order's
total is the cart's total, never re-derived by the model). Returns
`Command(graph=Command.PARENT, …)` — `Command.PARENT` propagates `order` to the outer
graph *and* ends the intake agent (the handoff). An empty cart returns a rejection
without `Command.PARENT`, so intake just continues.

### `fulfillment_agent.py` — the placing agent
Reads `state["order"]` and invokes a second `create_react_agent` whose only tool is
`send_order`, instructed to place the order immediately without asking questions. It
stays an agent (rather than a plain function) so more fulfillment tools can be added
later.

### `send_order.py` — dispatch
The real side effects, in order: (1) `validate_order` — reject and return an error if
anything's wrong, persisting nothing; (2) `orders_store.save_order` — write to SQLite,
get a row id; (3) `_post_to_webhook` — best-effort POST to `ORDER_WEBHOOK_URL` if set,
with a 5-second timeout and 3 attempts with backoff; (4) print the "ORDER PLACED"
block.

### `order_validation.py` — the trust boundary
`validate_order(items, total)` checks the order against the menu: non-empty, every
item on-menu, positive integer quantities, unit prices matching the menu, and the
total matching the menu-computed sum (with a small float tolerance). Raises
`OrderValidationError` otherwise. This is the deterministic guard described in §5.

### `orders_store.py` — SQLite history
A thin `sqlite3` wrapper over an `orders` table. `save_order(...)` inserts and returns
the id; `get_last_order()` powers reorder. The table is created on first connect (no
migrations). The DB path defaults to `orders.db` and is overridable via
`ORDERS_DB_PATH` (which is also how the test suite isolates each test).

### `fetch_last_order.py` — reorder lookup
A read-only tool that returns the customer's most recent order (or a "no previous
orders" message). The agent reads it back and re-adds the items via `add_to_cart` —
it doesn't place anything itself.

### `voice.py` — voice I/O (today)
`listen()` records from the mic until ~1.5s of silence, then transcribes with
mlx-whisper. `speak()` pipes text to macOS `say` and supports **barge-in**: it watches
the mic while talking and kills playback the instant the user starts speaking.

---

## 7. End-to-end: the life of a turn

A single user message ("two garlic naan and a mango lassi"):

1. `mealbot.py` calls `graph.invoke({"messages": [("user", "...")]}, config)`.
2. Outer graph: `START → intake`. The intake agent receives the full state
   (messages + cart + order).
3. The agent loops: model → tool → model → … Because parallel tool calls are off, it
   calls one tool at a time. Here it calls `add_to_cart("Garlic Naan", 2)`, the cart
   updates, then `add_to_cart("Mango Lassi", 1)`, the cart updates again — each call
   reads the latest cart.
4. The agent produces a reply ("Added! Your total is $13. Anything else?"). No
   `order` was set, so `route_after_intake → END`. The turn ends; the reply is shown.
5. **Next turn**, the customer says "yes, place it." This time the agent calls
   `save_order_details_to_graph`, which snapshots the cart into `order` and hands off
   via `Command.PARENT`.
6. `route_after_intake` sees `order` is set → routes to **fulfillment**.
7. The fulfillment agent calls `send_order` → `validate_order` passes → SQLite insert
   (#1) → optional webhook → "ORDER PLACED" printed.
8. `intake_complete(result)` sees `order` set → the REPL exits.

Memory across turns (steps 4→5) works because of the `MemorySaver` checkpointer keyed
by `thread_id`: messages, cart, and order are all restored on the next invoke.

---

## 8. Deep dives on the hard parts (interview gold)

### 8.1 Why multi-agent instead of one agent?
Separation of concerns. The **intake** agent's job is open-ended conversation with
many tools; the **fulfillment** agent's job is a tight, deterministic "place this
exact order." Splitting them keeps each prompt focused, makes the handoff explicit,
and leaves room to grow fulfillment (payment, delivery ETA, kitchen routing) without
bloating the intake prompt. The two communicate only through shared state — a clean
boundary.

### 8.2 The cart as graph state (InjectedState + Command)
The cart can't live in the model's head — that's exactly the unreliability we're
avoiding. So it's a real field in graph state. Tools **read** it with `InjectedState`
(LangGraph injects the current state into the tool call) and **write** it by returning
a `Command(update={"cart": new_cart, ...})`. Because the intake agent's state schema
(`IntakeState`) includes `cart`, the value flows into the tools and back out to the
outer graph automatically when the node finishes. This is *the* idiomatic LangGraph
pattern for stateful tools.

`Command.PARENT` is a related but distinct trick: the intake agent is a **subgraph**,
so a normal `Command` update stays inside it. `save_order_details_to_graph` uses
`graph=Command.PARENT` to push `order` up to the **outer** graph (and to terminate the
subgraph — the handoff). The cart tools deliberately *don't* use `Command.PARENT`:
they want to stay in the conversation, and the cart round-trips to the outer graph on
its own when the node returns.

### 8.3 The parallel tool-call race (a real bug I fixed)
First end-to-end test: the customer said "make that 3 and add a lassi." The model
emitted **two tool calls in one step** (update + add). Both ran in the same LangGraph
"superstep," both tried to write the `cart` channel, and LangGraph raised
`InvalidUpdateError: can receive only one value per step`. Worse, even without the
error it would be *wrong* — both tools read the same starting cart, so one edit would
clobber the other (stale-read / lost-update).

Fix: bind the model with **`parallel_tool_calls=False`**. Now the model emits at most
one tool call per step; the cart updates, then the model is called again and emits the
next one. Edits are serialized and each reads the latest cart. The trade-off is
slightly more model round-trips for multi-item turns, which is fine here. (A reducer
on the channel wouldn't fix the stale-read; serialization is the correct fix.)

### 8.4 Routing on `state["order"]`, not message contents
An earlier version detected the handoff by scanning messages for a tool name. That's
fragile — it depends on how LangGraph names tool messages. The robust version routes
on a **fact about state**: is `order` set? That's unambiguous, easy to test, and
decoupled from framework internals. General principle: route on state, not on string
matching.

### 8.5 Menu as data, not prompt text
Originally the menu was baked into the prompt and duplicated in the voice hint.
Pulling it into `menu.json` gave a single source of truth, made dietary/price queries
a real lookup (`query_menu`) instead of model reasoning, and let validation check
against the same prices the customer was quoted. One file drives the prompt, the
query tool, and the speech vocabulary hint.

### 8.6 Validation as a trust boundary
`validate_order` runs at the **dispatch** boundary — the last point before an order is
recorded or sent. It recomputes everything from the menu and rejects mismatches. Why
there and not during intake? Because it guarantees nothing invalid is *ever* persisted
or dispatched, regardless of how the order was assembled. The cart tools also validate
at add-time (fail fast for the user), so validation is defense-in-depth: friendly
checks up front, a hard guarantee at the boundary.

### 8.7 Resilient dispatch
The webhook POST has an explicit **timeout** and **retries with backoff**, and it's
**best-effort**: the order is already saved to SQLite, so a failed webhook is logged
and swallowed rather than failing the customer's order. This is the standard "persist
first, then notify" pattern — durability before side effects.

---

## 9. State & memory model

- **Within a turn:** the agent loop carries state through the subgraph.
- **Across turns:** `MemorySaver` + a fixed `thread_id` checkpoint the whole `State`
  (messages, cart, order), so the next `invoke` resumes with full context.
- **Across runs:** `MemorySaver` is in-memory, so a fresh process starts clean —
  except for **orders**, which are durably in SQLite (that's what powers reorder
  across sessions).

A natural follow-up question: "how would you scale to many concurrent customers?"
Answer: give each customer their own `thread_id` (today it's hard-coded to one), swap
`MemorySaver` for a persistent checkpointer (e.g. the SQLite/Postgres checkpointer
LangGraph ships), and run the graph behind a server.

---

## 10. Testing strategy

- **52 tests, fully offline** — no model calls, no network. They run in ~half a second,
  which makes them CI-friendly and fast to iterate on.
- **What's tested:** menu queries, all cart behaviors (add/merge/update/remove/total,
  and every validation rejection), order validation, routing, the confirmation
  snapshot, persistence round-trips, and webhook behavior (skipped when unset, retried
  on failure, order still succeeds when the webhook is down).
- **How the LLM is avoided:** routing and `intake_complete` are pure functions of
  state, so they're tested on plain dicts. Tools are tested directly. The order store
  uses a temp SQLite file per test via the `temp_orders_db` fixture.
- **One gotcha worth knowing:** tools that use `InjectedState` / `InjectedToolCallId`
  can't be called with plain `.invoke({...})` (the framework would normally inject
  those args). In tests they're called as `tool.func(name=..., state={...},
  tool_call_id=...)` to supply the injected args directly.

The thing to emphasize: **the deterministic core is 100% testable without the model**,
precisely because correctness lives in code, not in the prompt.

---

## 11. Voice today vs. a real phone call

### Today (local voice mode)
`voice.py` uses the computer's **mic and speaker**: mlx-whisper for speech-to-text,
macOS `say` for speech-out, with barge-in. It's a "record until silence → transcribe →
respond" loop. Great for a local demo; it is **not** a phone call (no telephony, and
it's batch transcription, not streaming).

### Making it a real phone agent
A phone call needs pieces this project doesn't have yet:
1. **Telephony** — a phone number and a bridge to the phone network (Twilio, Telnyx…).
2. **Live bidirectional audio streaming** — caller audio in, synthesized audio out, in
   telephony format (8 kHz μ-law).
3. **Streaming STT** — transcribe as the caller speaks (Deepgram, AssemblyAI…), not
   record-then-transcribe.
4. **Streaming TTS** — speak responses back over the call (ElevenLabs, Deepgram Aura…).
5. **Turn-taking / endpointing / barge-in** over the call.
6. **An always-on server** — telephony providers call *your* code via webhooks.
7. **Low latency** — calls feel broken above ~800 ms round-trip, which is why every
   step above must stream.

---

## 12. The Vapi + Twilio path (recommended phone implementation)

**Vapi** is a managed voice-AI platform that bundles most of §11 for you: it handles
the phone number (its own or a **Twilio** number you bring), real-time STT, TTS,
turn-taking, interruption, and latency. You don't wire Twilio and Vapi together as
peers — **Twilio is the phone number underneath Vapi**, and Vapi is the voice layer.

### How Mealbot plugs in
Vapi lets you configure a **Custom LLM**: instead of using a built-in model, you give
Vapi the URL of your own **OpenAI-compatible `/chat/completions` endpoint**. Each turn,
Vapi sends the conversation to that endpoint and streams your response back to the
caller as speech. So the plan is:

```
 Caller ── phone ──> Twilio number ──> Vapi (STT, TTS, turn-taking)
                                          │  per-turn: POST /chat/completions
                                          ▼
                              Your FastAPI server  ──>  LangGraph graph (the "brain")
                                  (cart, menu lookups, validation, ordering backend)
```

**What you build:** a small **FastAPI** server exposing an OpenAI-style
`/chat/completions` endpoint. Inside it, you:
1. Map the Vapi **call ID → a LangGraph `thread_id`** (so each caller has their own
   cart/state).
2. Feed the latest user turn into `graph.invoke(...)`.
3. Return the assistant's reply in the OpenAI chat-completion shape (streamed via SSE
   so Vapi can start speaking sooner).

**What you keep, unchanged:** the entire brain — multi-agent conversation, cart, menu
Q&A, validation, SQLite ordering backend. That's the hard, valuable part, and it ports
directly. **What changes:** the I/O edges (mic/speaker → telephony stream) and going
from a CLI REPL to a deployed server.

### Honest caveats to mention
- **Shape mismatch:** Vapi's Custom LLM expects OpenAI-compatible streaming chat
  completions; LangGraph thinks in graph state and messages. You write a thin adapter
  to translate between them. Not hard, but it's real work.
- **State keying:** today `thread_id` is hard-coded to one session. For phone you key
  it by Vapi's call ID and swap `MemorySaver` for a persistent checkpointer.
- **Tools:** you can either keep tool-calling inside your LangGraph brain (simplest, so
  the model logic stays in one place) or expose some as Vapi "functions" — keeping them
  in the brain is cleaner.

### The DIY alternative (no Vapi)
If you want to show lower-level depth: **Twilio Media Streams** (audio over WebSocket)
→ **Deepgram** (streaming STT) → your **LangGraph** brain → **ElevenLabs** (streaming
TTS), often orchestrated with **Pipecat** or **LiveKit Agents**. More wiring, more
control, and this is where Deepgram genuinely earns a place in the stack.

**Recommendation:** Vapi + a Twilio number to ship fast; the DIY pipeline if the goal
is to demonstrate telephony/streaming engineering depth.

---

## 13. Limitations & what I'd do next

- **Single session:** `thread_id` is hard-coded; multi-user needs per-user threads and
  a persistent checkpointer.
- **In-memory conversation:** only orders survive a restart; conversation memory is
  `MemorySaver` (in-process).
- **No payment / delivery / real kitchen integration** — `send_order` persists and
  optionally webhooks; it doesn't take payment.
- **No auth / identity** — "last order" is global, not per-customer; real reorder needs
  customer identity (a phone number would provide that naturally).
- **Voice is local-only** today (see §11–12 for the phone path).
- **Observability:** there's logging on dispatch but no metrics/tracing; I'd add
  structured logging and latency metrics before production.

---

## 14. Likely interview questions (with crisp answers)

**Q: Why LangGraph instead of just calling the Claude API in a loop?**
A: I need durable state (the cart), explicit control flow (intake → fulfillment), and
tool-calling agents with memory. LangGraph gives me a state machine with checkpointing
and a clean place for the agent/tool logic, instead of hand-rolling all of that.

**Q: How do you stop the LLM from getting prices or totals wrong?**
A: The model never owns those. Prices are looked up from `menu.json` in code, the
total is summed in Python, and every order is re-validated against the menu at the
dispatch boundary. The model drives conversation; code owns correctness.

**Q: Walk me through what happens when two tool calls happen at once.**
A: That was a real bug — two cart edits in one superstep collided on the state channel
and would have caused a lost update. I disabled parallel tool calls so edits serialize,
each reading the latest cart.

**Q: How is the order state shared between the two agents?**
A: Through the outer graph's `State`. The confirmation tool snapshots the cart into
`order` and pushes it to the outer graph with `Command.PARENT`; routing and the
fulfillment agent both read `state["order"]`.

**Q: How do you test an LLM app?**
A: I keep correctness in deterministic code and test that exhaustively offline — 52
tests, no model or network — covering cart logic, validation, routing, persistence,
and dispatch. The model's job (phrasing, tool choice) I verified with a few scripted
end-to-end runs, but it isn't what the unit tests depend on.

**Q: How would you turn this into a real phone system?**
A: Vapi for the voice layer (telephony via a Twilio number, streaming STT/TTS,
turn-taking) with my LangGraph brain behind a FastAPI Custom-LLM endpoint, keyed per
call. The brain ports unchanged; only the I/O edges and deployment change. (See §12.)

**Q: How would you scale to thousands of concurrent callers?**
A: Per-caller `thread_id`, a persistent checkpointer (SQLite/Postgres), the graph
behind a horizontally-scaled server, and a real datastore for orders. The compute is
mostly the model calls, so it scales with the LLM provider plus a stateless app tier.

**Q: What would you do differently / improve?**
A: Per-user identity and threads, payment + real fulfillment integration, structured
observability, and the streaming phone pipeline. See §13.

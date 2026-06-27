# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add ANTHROPIC_API_KEY
```

## Running

```bash
# Text mode
python mealbot.py

# Voice mode (Apple Silicon only — requires mlx-whisper)
python mealbot.py --voice
```

### Tests

```bash
python -m pytest            # whole suite
python -m pytest tests/test_tools.py::test_send_order_persists_and_returns_receipt  # one test
```

The suite is fully offline — no model or network calls. Routing/handoff are tested on plain state dicts, and the order store runs against a temp SQLite file (the `temp_orders_db` fixture sets `ORDERS_DB_PATH`).

Testing tools that use `InjectedState` / `InjectedToolCallId` (the cart tools and `save_order_details_to_graph`): call `tool.func(...)` directly and pass the injected args yourself (e.g. `add_to_cart.func(name=..., quantity=..., state={"cart": [...]}, tool_call_id="t")`). Plain `tool.invoke({...})` won't work — it expects the framework to inject `state`/`tool_call_id`.

Optional environment variables:
- `ORDER_WEBHOOK_URL` — if set, each placed order is also POSTed here as JSON (best-effort; failures are logged, not fatal).
- `ORDERS_DB_PATH` — override the SQLite order-history location (defaults to `orders.db` in the repo root).

## Architecture

Python CLI with two cooperating LangGraph agents. Orders persist to a local SQLite file (`orders.db`); no server, no frontend.

### Outer graph (`agent.py`)
Builds a `StateGraph` with two nodes — `intake` and `fulfillment` — connected by a conditional edge. Compiled with `MemorySaver` and a fixed `thread_id` so conversation history persists across REPL turns within a single run.

### Shared state (`state.py`)
`State` TypedDict with `messages` (history, merged via `add_messages`), `cart` (in-progress line items, replaced wholesale on each edit), and `order` (the cart snapshot taken at confirmation; its presence is what routes to fulfillment).

### Menu (`menu.json` + `menu.py`)
The menu is data, not prose. `menu.json` holds each item's `name`, `price`, and `tags` (dietary: `veg`/`vegan`/`contains-dairy`/`contains-gluten`/`mild`, plus a category). `menu.py` loads it once and is the single source consumed by the intake prompt (`format_menu_for_prompt`), the menu-query tool, and the voice transcription hint (`menu_item_names`).

### Intake agent (`intake_agent.py`)
`create_react_agent` (state schema extended to `IntakeState` so the cart is in scope) with tools: `query_menu`, `fetch_last_order`, the cart tools, and `save_order_details_to_graph`. Built on a model bound with `parallel_tool_calls=False` — cart tools each replace the whole cart, so two writes in one step would collide on the state channel and read stale state; one tool per step keeps every edit reading the latest cart.

### Menu query tool (`menu_query.py`)
`query_menu(dietary=[...], max_price=...)` filters `menu.json` by dietary tags and/or price so the agent answers "what's vegan / under $5 / not spicy?" from data instead of reasoning over the prompt. Stateless; AND-combines filters; returns an error string for an unknown filter.

### Cart tools (`cart.py`)
`add_to_cart` / `update_cart_item` / `remove_from_cart` / `view_cart` build `state["cart"]`. They read the current cart via `InjectedState` and return a `Command` that replaces it (no `graph=Command.PARENT` — the cart lives in the agent's own state and round-trips to the outer graph when the node returns). Prices are looked up from the menu here, not supplied by the model, and `cart_total` is the running total. Each tool validates (on-menu, positive integer quantity, spice 1–5) and returns a plain `ToolMessage` rejection on bad input, leaving the cart unchanged.

### `save_order_details_to_graph` tool (`save_order_details_to_graph.py`)
Confirmation/handoff. Reads the cart from `InjectedState` and snapshots it into `order` (so the total is the cart's, never re-derived by the model), returning `Command(graph=Command.PARENT, update={"order": {...}, "messages": [ToolMessage(...)]})`. `graph=Command.PARENT` both propagates `order` to the outer graph and ends the intake agent (the handoff). An empty cart returns a rejection without `graph=PARENT`, so intake continues.

### Fulfillment agent (`fulfillment_agent.py`)
Reads `state["order"]` directly, then invokes a `create_react_agent` with `send_order` as its tool. Designed to stay an agent because more tools will be added later.

### `send_order` tool (`send_order.py`)
The actual dispatch: first calls `validate_order` (rejects and returns an error string without persisting if the order is bad), then persists via `orders_store.save_order` (getting a row id), best-effort POSTs to `ORDER_WEBHOOK_URL` if set (5s timeout, 3 attempts with backoff), then prints the ORDER PLACED block.

### Order validation (`order_validation.py`)
`validate_order(items, total)` checks a confirmed order against `menu.json` — items on-menu, positive integer quantities, unit prices and total matching the menu (not whatever the model computed) — and raises `OrderValidationError` otherwise. This is the trust boundary: the model assembles prices/total during intake and can get them wrong.

### Order history (`orders_store.py`)
SQLite (`sqlite3`, stdlib) wrapper over the `orders` table. `save_order(...)` inserts and returns the id; `get_last_order()` powers the reorder flow. The table is created on first connect, so there's no migration step. This store is both the dispatch record and the history source.

### `fetch_last_order` tool (`fetch_last_order.py`)
Read-only tool for the intake agent. Returns the customer's most recent order (items, total, instructions, timestamp) or a "no previous orders" message. Informational only — it does not place anything.

### Entry point (`mealbot.py`)
REPL loop. `make_io(voice)` returns `get_input` / `send_output` callables that abstract voice vs text. Loop exits when `intake_complete()` sees `order` set in the result state.

### Prompts (`prompts.py`)
`INTAKE_PROMPT` and `FULFILLMENT_PROMPT` — the system prompts that govern each agent's behavior. `INTAKE_PROMPT` embeds the live menu via `format_menu_for_prompt()` and encodes the ordering rules (ask quantity/spice, read back the cart before confirming, never tally prices itself). Change agent behavior here, not in the agent builders.

### Routing logic
After the intake node runs, `route_after_intake` routes to fulfillment iff `state["order"]` is set (i.e. the cart was confirmed), else END (wait for the next user message). Keying on `order` rather than message contents keeps routing robust to how tool messages are named.

### Voice mode (`voice.py`)
`listen()` records from the mic until ~1.5s of silence, then transcribes with `mlx-whisper` (Apple Silicon only). `speak()` uses the macOS `say` command and supports barge-in: it monitors the mic while speaking and kills playback the moment the user starts talking.

## Related docs
- `PROJECT_GUIDE.md` — deeper architecture walkthrough, design-decision rationale, and the (not-yet-built) Vapi + Twilio phone-call design.
- `BACKLOG.md` — queued work, lead item being the voice-call integration.

## Key constraint
Model is always `claude-sonnet-4-6`. Do not change it.

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

Tests avoid the live model: routing/handoff use fake messages, and the order store runs against a temp SQLite file (the `temp_orders_db` fixture sets `ORDERS_DB_PATH`).

Optional environment variables:
- `ORDER_WEBHOOK_URL` — if set, each placed order is also POSTed here as JSON (best-effort; failures are logged, not fatal).
- `ORDERS_DB_PATH` — override the SQLite order-history location (defaults to `orders.db` in the repo root).

## Architecture

Python CLI with two cooperating LangGraph agents. Orders persist to a local SQLite file (`orders.db`); no server, no frontend.

### Outer graph (`agent.py`)
Builds a `StateGraph` with two nodes — `intake` and `fulfillment` — connected by a conditional edge. Compiled with `MemorySaver` and a fixed `thread_id` so conversation history persists across REPL turns within a single run.

### Shared state (`state.py`)
`State` TypedDict with `messages` (full conversation history, merged via `add_messages`) and `order` (confirmed order dict, set by the intake tool).

### Menu (`menu.json` + `menu.py`)
The menu is data, not prose. `menu.json` holds each item's `name`, `price`, and `tags`. `menu.py` loads it once and is the single source consumed by the intake prompt (`format_menu_for_prompt`) and the voice transcription hint (`menu_item_names`) — edit the menu in one place, not three.

### Intake agent (`intake_agent.py`)
`create_react_agent` with two tools: `fetch_last_order` (reorder lookup) and `save_order_details_to_graph` (handoff). Collects items, quantity, and spice level (1–5). When the customer asks for "the usual"/"same as last time", it calls `fetch_last_order`, reads the result back, and only hands off after explicit confirmation.

### `save_order_details_to_graph` tool (`save_order_details_to_graph.py`)
Returns `Command(graph=Command.PARENT, update={"order": {...}, "messages": [ToolMessage(...)]})`. `graph=Command.PARENT` is critical: it propagates the update to the outer `StateGraph` so the fulfillment node can read `state["order"]`, rather than leaving it in the intake react-agent's inner state. The `ToolMessage` is also required — LangGraph rejects a tool call that has no matching tool response.

### Fulfillment agent (`fulfillment_agent.py`)
Reads `state["order"]` directly (set by the intake tool above), then invokes a `create_react_agent` with `send_order` as its tool. Designed to stay an agent because more tools will be added later.

### `send_order` tool (`send_order.py`)
The actual dispatch: first calls `validate_order` (rejects and returns an error string without persisting if the order is bad), then persists via `orders_store.save_order` (getting a row id), best-effort POSTs to `ORDER_WEBHOOK_URL` if set (5s timeout, 3 attempts with backoff), then prints the ORDER PLACED block.

### Order validation (`order_validation.py`)
`validate_order(items, total)` checks a confirmed order against `menu.json` — items on-menu, positive integer quantities, unit prices and total matching the menu (not whatever the model computed) — and raises `OrderValidationError` otherwise. This is the trust boundary: the model assembles prices/total during intake and can get them wrong.

### Order history (`orders_store.py`)
SQLite (`sqlite3`, stdlib) wrapper over the `orders` table. `save_order(...)` inserts and returns the id; `get_last_order()` powers the reorder flow. The table is created on first connect, so there's no migration step. This store is both the dispatch record and the history source.

### `fetch_last_order` tool (`fetch_last_order.py`)
Read-only tool for the intake agent. Returns the customer's most recent order (items, total, instructions, timestamp) or a "no previous orders" message. Informational only — it does not place anything.

### Entry point (`mealbot.py`)
REPL loop. `make_io(voice)` returns `get_input` / `send_output` callables that abstract voice vs text. Loop exits when `intake_complete()` detects `save_order_details_to_graph` in the result messages.

### Routing logic
After the intake node runs, `route_after_intake` checks if `save_order_details_to_graph` appears in messages. If yes → fulfillment node. If no → END (wait for next user message).

### Voice mode (`voice.py`)
`listen()` records from the mic until ~1.5s of silence, then transcribes with `mlx-whisper` (Apple Silicon only). `speak()` uses the macOS `say` command and supports barge-in: it monitors the mic while speaking and kills playback the moment the user starts talking.

## Key constraint
Model is always `claude-sonnet-4-6`. Do not change it.

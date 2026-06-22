# mealbot

A conversational food ordering agent powered by Claude AI. Place orders in plain English via text or voice — the agent clarifies, confirms, and places your order.

## Demo

```
Welcome to Mealbot! What would you like to order today?

You: I'd like some dal makhani and two garlic naans
Bot: Great choice! Just to confirm your order:

     • Dal Makhani x1 — $10.00
     • Garlic Naan x2 — $8.00
     Total: $18.00

     Shall I go ahead and place this order?

You: yes

========================================
ORDER PLACED  (#1)
========================================
  1x Dal Makhani @ $10.00 = $10.00
  2x Garlic Naan @ $4.00  = $8.00
  TOTAL                      $18.00
========================================

Bot: Your order has been placed! Enjoy your meal!
```

## Features

- **Natural language ordering** — say what you want, the agent figures out the rest
- **Menu Q&A & dietary filters** — ask "what's vegan?", "anything under $5?", "what's gluten-free / not spicy?"; answered from the menu data, not guesswork
- **Live cart** — add, change quantity/spice, or remove items mid-conversation with a running total
- **Order confirmation** — always reads back the full cart before placing
- **Reorder** — "the usual" / "same as last time" pulls up your previous order
- **Validation** — prices and totals are checked against the menu before an order is placed
- **Persistence & dispatch** — every order is saved to a local SQLite history and, optionally, POSTed to a webhook
- **Voice mode** — speak your order; agent responds out loud with barge-in support
- **Off-menu handling** — politely rejects unavailable items and suggests alternatives

## Tech stack

| Layer | Technology |
|---|---|
| Agent framework | [LangGraph](https://github.com/langchain-ai/langgraph) (multi-agent `StateGraph`) |
| LLM | Claude `claude-sonnet-4-6` via [LangChain Anthropic](https://python.langchain.com/docs/integrations/chat/anthropic/) |
| Order history | SQLite (`sqlite3`, stdlib) |
| Speech-to-text | [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) (Apple Silicon) |
| Text-to-speech | macOS `say` (built-in) |
| Tests | [pytest](https://docs.pytest.org/) (fully offline) |

## Requirements

- Python 3.11+
- Apple Silicon Mac (for voice mode)
- [Anthropic API key](https://console.anthropic.com/)

## Installation

```bash
git clone https://github.com/ayushgupta75/mealbot.git
cd mealbot

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
```

Open `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=your_key_here
```

## Usage

**Text mode**
```bash
python mealbot.py
```

**Voice mode**
```bash
python mealbot.py --voice
```

> First run in voice mode downloads the Whisper model (~800MB). Subsequent runs load it from cache.

Type or say `bye` to exit at any time.

## Configuration

### Menu
The menu is data. Edit `menu.json` to define items, prices, and dietary tags — the intake prompt, the menu-query tool, and the voice transcription hint all read from it:

```json
[
  { "name": "Dal Makhani", "price": 10, "tags": ["main", "veg", "contains-dairy", "mild"] },
  { "name": "Garlic Naan", "price": 4,  "tags": ["bread", "veg", "contains-dairy", "contains-gluten", "mild"] },
  { "name": "Mango Lassi", "price": 5,  "tags": ["drink", "veg", "contains-dairy", "mild"] }
]
```

### Environment variables
| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required. Your Anthropic API key. |
| `ORDER_WEBHOOK_URL` | Optional. If set, each placed order is also POSTed here as JSON (best-effort; timeout + retry). |
| `ORDERS_DB_PATH` | Optional. Override the SQLite order-history location (defaults to `orders.db`). |

## Tests

```bash
python -m pytest                 # whole suite (offline — no model or network calls)
python -m pytest tests/test_cart.py::test_running_total_sums_line_totals   # a single test
```

## Project structure

```
mealbot/
├── mealbot.py                      # Entry point — argument parsing and REPL loop
├── agent.py                        # Outer StateGraph: intake + fulfillment nodes, routing
├── state.py                        # Shared State (messages, cart, order)
├── intake_agent.py                 # Intake react-agent (menu Q&A + cart building)
├── fulfillment_agent.py            # Fulfillment react-agent (places the confirmed order)
├── prompts.py                      # Intake/fulfillment prompts (menu block built from menu.json)
├── menu.json / menu.py             # Menu data and loader (single source of truth)
├── menu_query.py                   # query_menu tool — dietary/price lookups
├── cart.py                         # Cart tools: add / update / remove / view
├── save_order_details_to_graph.py  # Confirmation tool — snapshots cart into the order
├── order_validation.py             # Validates an order against the menu before dispatch
├── send_order.py                   # Dispatch — validate, persist to SQLite, optional webhook
├── orders_store.py                 # SQLite order history (save_order / get_last_order)
├── fetch_last_order.py             # Reorder lookup tool
├── voice.py                        # listen() and speak() for voice I/O
├── tests/                          # Offline pytest suite
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT

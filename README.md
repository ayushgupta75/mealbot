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
ORDER PLACED
========================================
  1x Dal Makhani @ $10.00 = $10.00
  2x Garlic Naan @ $4.00  = $8.00
  TOTAL                      $18.00
========================================

Bot: Your order has been placed! Enjoy your meal!
```

## Features

- **Natural language ordering** — say what you want, the agent figures out the rest
- **Clarifying questions** — agent asks about quantities, variants, and missing details
- **Order confirmation** — always reads back the full order before placing
- **Voice mode** — speak your order; agent responds out loud with barge-in support
- **Off-menu handling** — politely rejects unavailable items and suggests alternatives

## Tech stack

| Layer | Technology |
|---|---|
| Agent framework | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM | Claude `claude-sonnet-4-6` via [LangChain Anthropic](https://python.langchain.com/docs/integrations/chat/anthropic/) |
| Speech-to-text | [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) (Apple Silicon) |
| Text-to-speech | macOS `say` (built-in) |

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
Edit the `MENU` section in `prompts.py` to define your restaurant's items and prices:

```python
MENU:
- Dal Makhani    $10
- Garlic Naan    $4
- Mango Lassi    $5
```

## Project structure

```
mealbot/
├── mealbot.py       # Entry point — argument parsing and REPL loop
├── agent.py         # LangGraph agent setup (model, tools, memory)
├── prompts.py       # System prompt with menu and agent behavior rules
├── send_order.py    # send_order tool — prints confirmed order to terminal
├── voice.py         # listen() and speak() for voice I/O
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT

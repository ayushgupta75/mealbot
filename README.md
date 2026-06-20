# mealbot

A voice-enabled food ordering agent powered by Claude. Speak (or type) your order, the agent clarifies and confirms, then places it.

## How it works

- **LangGraph** manages the agent loop with Claude (`claude-sonnet-4-6`)
- **`send_order` tool** is called only after you explicitly confirm — prints the structured order to terminal
- **Voice mode** uses `mlx-whisper` (Apple Silicon) for speech-to-text and macOS `say` for text-to-speech with barge-in support
- Stateless — no database, no auth

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

## Usage

**Text mode**
```bash
python mealbot.py
```

**Voice mode** (Apple Silicon Mac only)
```bash
python mealbot.py --voice
```

In voice mode, speak your order. The bot responds out loud. Interrupt it anytime by speaking. Say **"bye"** to exit.

## Menu

Edit the `MENU` section in `prompts.py` to set your restaurant's items and prices.

## Project structure

```
mealbot.py      # entry point — REPL loop
agent.py        # builds the LangGraph agent
prompts.py      # system prompt and menu
send_order.py   # @tool that prints the confirmed order
voice.py        # listen() and speak() for voice mode
```

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
python mealbot.py
```

## Architecture

Four-file Python CLI. No server, no database, no frontend.

- **`prompts.py`** — `SYSTEM_PROMPT` constant containing the hardcoded menu and agent behavior rules
- **`send_order.py`** — LangChain `@tool` that prints a confirmed order to stdout and returns `"Order received."`
- **`agent.py`** — `build_agent()` wires together `ChatAnthropic(claude-sonnet-4-6)`, the `send_order` tool, and a `MemorySaver` checkpointer into a LangGraph `create_react_agent`; returns `(graph, config)`
- **`mealbot.py`** — entry point; calls `build_agent()` once, runs a REPL loop, exits automatically when `send_order` fires

The agent uses a fixed `thread_id` (`"session-1"`) so conversation history persists across REPL turns within a single run. Each new run of `mealbot.py` starts a fresh session.

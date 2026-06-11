# MCP_3 — A *Real* MCP Project (Notes Manager + Claude)

This is a small but **complete and correct** Model Context Protocol (MCP) project.
Unlike `MCP_2` and `MCP_GAMIL_TOOL` (which were FastAPI HTTP endpoints you *called*
"MCP"), this one speaks the **actual MCP protocol** using the official SDK.

It is intentionally simple so you can focus on **how MCP really works**.

```
You (in terminal)
   │  "Add a note: buy milk"
   ▼
client.py  ──► Claude (decides to use a tool)
   │                │
   │   MCP (JSON-RPC over stdio)
   ▼                ▼
mcp_server.py  ──►  storage.py  ──►  notes_db.json
 (tools/resources/prompts)   (plain logic)     (data)
```

## What's inside

| File | Role | Knows about MCP? |
|------|------|------------------|
| `mcp_server.py` | The **MCP server**: exposes tools, resources, prompts | ✅ yes |
| `storage.py` | Plain notes logic (add/list/search/delete) | ❌ no (on purpose) |
| `client.py` | The **AI host/client**: connects to the server, lets Claude use the tools | ✅ yes |
| `notes_db.json` | The data file (created at runtime) | — |
| `docs/` | **Full explanation, beginner → architect** | — |

## Quick start

```bash
# 1. From the repo root, use the existing virtualenv (mcp + anthropic already installed)
cd MCP_3

# (or install fresh into any venv)
# pip install -r requirements.txt

# 2. Add your Anthropic API key
cp .env.example .env
#   then edit .env and paste your key from https://console.anthropic.com/

# 3. Run the AI client (it launches the server for you automatically)
../.venv/bin/python client.py
```

Then chat:
```
You> Add a note titled Groceries: buy milk and eggs, tag it shopping
You> What notes do I have?
You> Search my notes for milk
You> Delete the groceries note
```

You do **not** start `mcp_server.py` yourself — `client.py` launches it as a
subprocess and talks to it over stdio. That's how MCP hosts (like Claude Desktop)
work too.

## Read the docs in order

Start here → [`docs/00_START_HERE.md`](docs/00_START_HERE.md)

1. `01_what_is_mcp.md` — what MCP is and the problem it solves
2. `02_architecture.md` — host/client/server, transports, JSON-RPC, the 3 primitives
3. `03_old_vs_real_mcp.md` — **why your MCP_2 wasn't real MCP** (key lesson)
4. `04_code_walkthrough.md` — every line of this project explained
5. `05_architect_level.md` — security, scaling, deployment, design patterns
6. `06_learning_resources.md` — videos, courses, official docs to go deeper

# 00 — Start Here: Your MCP Learning Path

Welcome. This folder takes you from **"what even is MCP"** to **"I can design an
MCP system at an architect level."** Read the docs in order, but here is the map
so you always know where you are.

## The 30-second version

> **MCP (Model Context Protocol)** is a standard "USB-C port for AI."
> It lets an AI app (like Claude) plug into your tools and data through one
> common protocol, instead of writing custom glue code for every integration.
>
> - **Server** = exposes capabilities (tools, data, prompts). *You build these.*
> - **Client/Host** = the AI app that uses them (Claude Desktop, Claude Code, Cursor…).
> - **Protocol** = JSON-RPC 2.0 messages over a transport (stdio or HTTP).

You just built one of each in this project.

## The learning path (beginner → architect)

```
LEVEL 1 — BEGINNER  "I understand the idea"
  └─ 01_what_is_mcp.md          Why MCP exists, the analogy, the vocabulary

LEVEL 2 — PRACTITIONER  "I can read and build one"
  ├─ 02_architecture.md         How the pieces talk (transports, JSON-RPC, primitives)
  ├─ 03_old_vs_real_mcp.md      Why your earlier projects weren't *real* MCP
  └─ 04_code_walkthrough.md     This project, explained line by line

LEVEL 3 — ARCHITECT  "I can design a system with it"
  ├─ 05_architect_level.md      Security, auth, scaling, deployment, patterns
  └─ 06_learning_resources.md   Videos, courses, specs to keep going
```

## How to actually learn this (not just read)

Reading alone won't make you an architect. Do this loop:

1. **Run it.** Follow the README quick start. Chat with your notes.
2. **Break it.** Add a bug, rename a tool, remove a docstring — watch what changes.
3. **Extend it.** Add a new tool (e.g. `edit_note`). This is the fastest way to learn.
4. **Explain it.** Try to describe the request flow out loud without looking. If you
   stumble, re-read `02_architecture.md`. Teaching = understanding.
5. **Compare.** Read `03_old_vs_real_mcp.md` against your `MCP_2/` code.

## Suggested first exercises (in increasing difficulty)

1. Add an `edit_note(note_id, title, content)` tool to `mcp_server.py`.
2. Make `list_notes` accept an optional `tag` filter.
3. Add a new resource `notes://tags` that lists all unique tags.
4. Add a prompt `weekly_summary()`.
5. Connect this same server to **Claude Desktop** (instructions in
   `05_architect_level.md`) — same server, a different host. This is the
   "aha!" moment for why a *standard* protocol matters.

When you finish, you'll genuinely understand MCP. Let's go → `01_what_is_mcp.md`.

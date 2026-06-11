# 01 — What is MCP, and Why Does It Exist?

## The problem MCP solves

An LLM (like Claude or GPT) on its own is a brain in a jar. It can reason and write,
but it **cannot**:
- read your files,
- query your database,
- send an email,
- look something up in your company wiki.

To make an AI *useful*, you connect it to tools and data. Before MCP, **everyone
invented their own way** to do this. If you had:

- 4 AI apps (Claude Desktop, Cursor, your own bot, a customer support tool), and
- 5 systems to connect (Gmail, GitHub, Postgres, Slack, your wiki),

you potentially wrote **4 × 5 = 20** custom integrations. Every app spoke to every
tool in its own private way. This is the classic "M×N problem."

```
        BEFORE MCP (M×N custom integrations)

  Claude ─┐   ┌─ Gmail
  Cursor ─┼───┼─ GitHub        every line = custom glue code
  MyBot  ─┼───┼─ Postgres      written by hand, repeated everywhere
  Support─┘   └─ Slack
        (a tangled mess)
```

## The solution: one standard protocol

MCP turns that into an **M + N** problem. Each AI app learns to speak MCP **once**.
Each tool is wrapped as an MCP **server** **once**. Now anything that speaks MCP can
talk to anything that exposes MCP.

```
        WITH MCP (M + N, via one standard)

  Claude ─┐                    ┌─ Gmail server
  Cursor ─┤                    ├─ GitHub server
  MyBot  ─┼──►  MCP protocol ──┼─ Postgres server
  Support─┘    (the standard)  └─ Slack server
```

This is why the official analogy is:

> **MCP is "a USB-C port for AI applications."**
> One standard plug. Any compliant device works with any compliant host.

Before USB, every device had its own connector. MCP is doing for AI-tool
connections what USB did for hardware.

## Where MCP came from (context for interviews / architecture talks)

- Created and open-sourced by **Anthropic** (the makers of Claude) in **late 2024**.
- It is an **open standard**, not an Anthropic-only thing. OpenAI, Google, and many
  tools/IDEs have adopted it. Servers you write work across hosts.
- The spec lives at **modelcontextprotocol.io** and is versioned (dated, e.g.
  `2025-06-18`). It evolves — that's normal for a protocol.

## The core vocabulary (memorize these 6 words)

| Term | Plain meaning | In this project |
|------|---------------|-----------------|
| **Host** | The AI app the human uses | `client.py` (a tiny host) / Claude Desktop |
| **Client** | The connector *inside* a host that talks to ONE server | the `ClientSession` in `client.py` |
| **Server** | A program that exposes capabilities | `mcp_server.py` |
| **Tool** | An action the AI can DO (a function it can call) | `add_note`, `delete_note` |
| **Resource** | Data the AI can READ (like a file/endpoint) | `notes://all` |
| **Prompt** | A reusable prompt template the server offers | `daily_review` |

A host can connect to **many** servers at once (one client per server). That's how
Claude Desktop can use your notes server *and* a GitHub server *and* a database
server simultaneously.

## A crucial distinction: MCP vs "function calling"

You already used **function calling / tool calling** in `MCP_GAMIL_TOOL` — you handed
the LLM a list of tool descriptions and it picked one. People confuse this with MCP.

- **Function calling** = a feature of the *LLM API* (the model decides which tool to
  call). It says nothing about *how* the tool is implemented or discovered.
- **MCP** = a *protocol* for how an app **discovers and talks to** external tools,
  in a standard, reusable, language-agnostic way.

They work **together**: MCP gives you the tools and their schemas; function calling
is how the model chooses among them. In `client.py` you'll see exactly this seam —
we fetch tools *via MCP*, then pass them to Claude's *function-calling* API.

## Why a beginner should care about the "standard" part

Because of the standard, the server you wrote in this project can be plugged into
**Claude Desktop, Claude Code, Cursor, Zed, and your own client** — *without changing
a line of server code*. You write the integration once; it works everywhere. That
reusability is the entire point, and it's what makes MCP an architectural building
block rather than a one-off script.

Next → `02_architecture.md` (how the messages actually flow).

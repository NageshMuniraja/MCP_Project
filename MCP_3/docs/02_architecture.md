# 02 — MCP Architecture: How the Pieces Actually Talk

This is the most important doc. Once the request flow clicks, everything else is detail.

## The three roles (precise definitions)

```
┌──────────────────────────── HOST (the AI application) ────────────────────────────┐
│  e.g. Claude Desktop, Claude Code, Cursor, or our client.py                        │
│                                                                                    │
│   ┌─────────── CLIENT ───────────┐    ┌─────────── CLIENT ───────────┐             │
│   │ MCP connector (1 per server) │    │ MCP connector (1 per server) │             │
│   └──────────────┬───────────────┘    └──────────────┬───────────────┘             │
└──────────────────┼───────────────────────────────────┼────────────────────────────┘
                   │  MCP (JSON-RPC 2.0)                │
                   ▼                                    ▼
         ┌──────── SERVER ────────┐           ┌──────── SERVER ────────┐
         │   notes-manager        │           │   github               │
         │ tools/resources/prompts│           │ tools/resources/prompts│
         └────────────────────────┘           └────────────────────────┘
```

- **Host**: the app the human interacts with. It holds the LLM connection and the UI.
- **Client**: a component *inside* the host. **Exactly one client per server.** It
  manages the connection and the message exchange with that one server.
- **Server**: your program. It advertises capabilities and answers requests. It does
  **not** contain an LLM — it just exposes tools/data.

Key idea: a host can run **many** clients, each wired to a different server. That's
multi-tool AI.

## The transport layer (how bytes move)

MCP messages travel over a **transport**. Two standard ones:

### 1. STDIO (what this project uses)
The host **launches the server as a subprocess** and talks to it through the
process's **standard input/output** streams.

```
client.py  ──spawns──►  python mcp_server.py
   write ──────────────►  server's stdin   (requests)
   read  ◄──────────────  server's stdout  (responses)
```

- ✅ Simplest. No network, no ports, no auth needed.
- ✅ Perfect for local tools (your machine, your files).
- ❌ Server runs on the same machine as the host. One client per process.
- This is why you **don't** run `mcp_server.py` yourself — the host spawns it.

> Note: the server uses **stdout** for protocol messages, so a server must **never**
> `print()` random text to stdout. Log to **stderr** instead. (FastMCP handles this;
> just remember it when debugging.)

### 2. Streamable HTTP (for remote / networked servers)
The server runs as a web service; the host connects over HTTP. Used when the server
is remote, shared by many users, or deployed in the cloud. Supports streaming via
Server-Sent Events (SSE). (An older "HTTP+SSE" transport is being replaced by the
newer **Streamable HTTP** transport in current spec versions.)

- ✅ Remote, multi-user, scalable, can sit behind auth (OAuth).
- ❌ More moving parts: networking, authentication, deployment.

**Rule of thumb:** local/personal tool → **stdio**. Shared/remote service → **HTTP**.
Your business logic (`storage.py`) doesn't change either way — only how it's served.

## The message format: JSON-RPC 2.0

MCP doesn't invent a new wire format; it uses **JSON-RPC 2.0**. You rarely see it
(the SDK hides it), but knowing it makes debugging painless. There are 3 message types:

```jsonc
// REQUEST (expects a response; has an id)
{ "jsonrpc": "2.0", "id": 1, "method": "tools/call",
  "params": { "name": "add_note", "arguments": { "title": "x", "content": "y" } } }

// RESPONSE (answers a request with the same id)
{ "jsonrpc": "2.0", "id": 1,
  "result": { "content": [ { "type": "text", "text": "{...}" } ] } }

// NOTIFICATION (fire-and-forget; NO id, no response expected)
{ "jsonrpc": "2.0", "method": "notifications/initialized" }
```

Common methods you'll see: `initialize`, `tools/list`, `tools/call`,
`resources/list`, `resources/read`, `prompts/list`, `prompts/get`.

## The connection lifecycle

Every MCP session follows the same handshake. This is the **capability negotiation**
that makes the protocol robust across versions.

```
CLIENT                                   SERVER
  │  1. initialize  (my version, my capabilities)
  │ ─────────────────────────────────────►
  │                 2. initialize result (its version, its capabilities)
  │ ◄─────────────────────────────────────
  │  3. notifications/initialized  (ok, we're synced)
  │ ─────────────────────────────────────►
  │
  │  4. tools/list / resources/list / prompts/list   (discovery)
  │ ──────────────────────────────────────►
  │ ◄──────────────────────────────────────
  │
  │  5. tools/call  ... (actual work, repeated) ...
  │ ◄──────────────────────────────────────►
  │
  │  6. close / process exit
```

In `client.py` you can map these directly:
- `await session.initialize()` → steps 1–3.
- `await session.list_tools()` → step 4.
- `await session.call_tool(...)` → step 5.

## The three server primitives (what a server can offer)

This is the heart of MCP design. Memorize the verbs.

| Primitive | Think of it as | Who controls it | Side effects? | In this project |
|-----------|----------------|-----------------|---------------|-----------------|
| **Tools** | Functions / verbs | the **model** decides to call | Yes (can change things) | `add_note`, `delete_note`… |
| **Resources** | Files / nouns (GET-like) | the **app/user** chooses to load | No (read-only) | `notes://all` |
| **Prompts** | Slash-commands / templates | the **user** picks | No | `daily_review` |

A useful way to remember **who is in control**:
- **Tools are model-controlled** — the AI decides when to call them.
- **Resources are application-controlled** — the host/user decides what to load.
- **Prompts are user-controlled** — the user explicitly invokes them.

### There are also *client*-side capabilities (advanced, good to know)
The server can ask the client for things too:
- **Sampling** — the server asks the *host's LLM* to generate text. Lets a server
  use AI without having its own API key. (Host must allow it.)
- **Roots** — the client tells the server which filesystem/URL "roots" it may use.
- **Elicitation** — the server asks the *user* for input mid-task (newer spec).

You don't need these for the notes project, but architects should know they exist —
they're how MCP supports richer, two-way workflows.

## The full request flow in THIS project (trace it once, slowly)

```
1. You type:  "Add a note: buy milk"            (in client.py REPL)
2. client.py sends your text + the tool list to Claude (Anthropic API).
3. Claude replies: stop_reason="tool_use", wants add_note(title=..., content=...).
4. client.py calls  session.call_tool("add_note", {...})
       └─► MCP request  {method:"tools/call", ...}  travels over stdio
5. mcp_server.py receives it, runs add_note(), which calls storage.add_note()
6. storage.py writes to notes_db.json and returns the new note
7. The result travels back over stdio to client.py
8. client.py sends that tool result back to Claude
9. Claude writes a final sentence: "Done — I saved your note about buying milk."
10. client.py prints it. Loop ends.
```

Steps 4–7 are **MCP**. Steps 2–3 and 8–9 are **function calling**. That seam — MCP
for *connecting to tools*, function calling for *choosing tools* — is the whole game.

Next → `03_old_vs_real_mcp.md` (why your earlier projects skipped steps 4–7).

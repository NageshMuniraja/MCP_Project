# 04 — Code Walkthrough (Every Part Explained)

Read this with the three files open: `storage.py`, `mcp_server.py`, `client.py`.
We go in the order it's easiest to understand: data → server → client.

---

## Part A — `storage.py` (plain logic, no MCP)

This file is deliberately boring and knows nothing about MCP or AI. That's the point.

```python
DB_PATH = Path(__file__).parent / "notes_db.json"
```
- The "database" is one JSON file next to the script. Open it after you add notes —
  you can literally read your data. Great for learning; you'd use a real DB in prod.

```python
def add_note(title, content, tags=None) -> dict:
    notes = _load()
    note = {"id": uuid.uuid4().hex[:8], "title": title, ...}
    notes.append(note); _save(notes); return note
```
- Each function is small and testable on its own. **Architect habit:** keep core
  business logic free of framework/protocol code so you can reuse and unit-test it.
  Today MCP serves it; tomorrow a REST API or CLI could serve the *same* functions.

There is nothing MCP-specific here, and that separation is intentional — see how
thin the server becomes because of it.

---

## Part B — `mcp_server.py` (the MCP server)

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("notes-manager")
```
- `FastMCP` is the high-level helper in the official SDK. The string `"notes-manager"`
  is the server's name, shown in host UIs (e.g. Claude Desktop's tool list).

### Tools — `@mcp.tool()`

```python
@mcp.tool()
def add_note(title: str, content: str, tags: list[str] | None = None) -> dict:
    """Create a new note. Use this whenever the user wants to save..."""
    return storage.add_note(title, content, tags)
```

Three things the decorator does **for free** — this is the magic vs. your old approach:

1. **Input schema from type hints.** `title: str, content: str, tags: list[str]|None`
   becomes a JSON Schema the client discovers via `tools/list`. You write it **once**.
2. **Description from the docstring.** The AI reads this to decide *when* to call the
   tool. So write docstrings **for the model**: say *when* to use it, not just *what*
   it does. Compare `add_note`'s docstring ("whenever the user wants to save…").
3. **Registration.** The function is now an MCP tool, discoverable and callable.

```python
@mcp.tool()
def get_note(note_id: str) -> dict:
    note = storage.get_note(note_id)
    if note is None:
        raise ValueError(f"No note found with id '{note_id}'")
    return note
```
- **Errors:** just `raise`. FastMCP converts the exception into a proper MCP tool
  error result, which the client (and Claude) can see and react to — e.g. Claude might
  apologize and try `list_notes` to find the right id. You don't return error JSON by hand.

### Resources — `@mcp.resource(uri)`

```python
@mcp.resource("notes://all")
def all_notes_resource() -> str:
    ...
```
- A **resource** is read-only data addressed by a **URI**. `notes://` is a custom
  scheme you invented (resources don't have to be `http://` or `file://`).
- Difference from a tool: a tool is a *verb the model calls*; a resource is a *noun
  the host/user loads into context*. Same data can be both (we expose notes both ways).

```python
@mcp.resource("notes://{note_id}")
def single_note_resource(note_id: str) -> str:
    ...
```
- The `{note_id}` makes it a **templated resource**: `notes://a1b2c3d4` fills in the
  id. Like a path parameter in a web route.

### Prompts — `@mcp.prompt()`

```python
@mcp.prompt()
def daily_review(focus: str = "everything") -> str:
    return "Please review my notes (focus on: {focus})... call list_notes... suggest 3 actions."
```
- A **prompt** is a reusable, parameterized message the **server ships** and the
  **user picks** (in Claude Desktop it shows up as a slash-command/menu item).
- Why server-side prompts? So good prompt wording lives *with* the tool that needs it
  and is standardized across every user/host. The user supplies `focus`; the server
  supplies the carefully-worded instructions.

### Entry point

```python
if __name__ == "__main__":
    mcp.run()
```
- `mcp.run()` with no args = **stdio transport**. It reads JSON-RPC requests from
  stdin and writes responses to stdout. To serve over HTTP instead you'd pass a
  transport argument (covered in `05_architect_level.md`). The *tools don't change* —
  only the transport.

---

## Part C — `client.py` (the AI host/client)

This is where MCP and the LLM meet. Read it top-to-bottom; here are the load-bearing parts.

### Telling MCP how to start the server

```python
SERVER_PARAMS = StdioServerParameters(command="python", args=["mcp_server.py"])
```
- The client will **spawn** `python mcp_server.py` and talk to it over stdio. This is
  why you never launch the server yourself. A different host (Claude Desktop) has its
  own config that says the same thing in JSON.

### The adapter (the only "glue" left)

```python
def mcp_tools_to_anthropic(mcp_tools):
    return [{"name": t.name, "description": t.description or "",
             "input_schema": t.inputSchema} for t in mcp_tools]
```
- MCP and Anthropic both describe tools as name + description + JSON schema, but use
  slightly different field names (`inputSchema` vs `input_schema`). This 4-line
  function is the entire translation. Contrast with the ~150 lines you needed in
  `MCP_GAMIL_TOOL` — because there, schemas weren't discovered, they were hand-parsed.

### Opening the session (the lifecycle from doc 02)

```python
async with stdio_client(SERVER_PARAMS) as (read, write):      # spawn + transport
    async with ClientSession(read, write) as session:         # MCP session
        await session.initialize()                            # handshake (steps 1-3)
        tool_list = (await session.list_tools()).tools        # discovery (step 4)
```
- `async with` ensures the subprocess and streams are cleaned up when you exit.
- `initialize()` performs the capability-negotiation handshake. **Required** before
  any other call.
- `list_tools()` is **discovery** — the client learns the tools at runtime. The whole
  reason the same client works with *any* MCP server.

### The agent loop (where Claude decides)

```python
while True:
    response = anthropic.messages.create(model=MODEL, messages=messages, tools=tools)
    ...
    if response.stop_reason != "tool_use":
        return                      # Claude gave a final answer; done
    # else: Claude asked to call one or more tools
    for block in response.content:
        if block.type == "tool_use":
            result = await session.call_tool(block.name, block.input or {})   # ← MCP call
            tool_results.append({"type":"tool_result","tool_use_id":block.id,"content":text})
    messages.append({"role":"user","content":tool_results})    # feed results back
```

Walk through one turn:
1. Send the conversation + discovered tools to Claude.
2. If `stop_reason == "tool_use"`, Claude wants a tool. We loop over the tool_use
   blocks (it can request several at once).
3. `session.call_tool(...)` is the **real MCP request** to the server (doc 02, step 5).
4. We append the results as a `tool_result` (matched to Claude's request by
   `tool_use_id`) and send them back.
5. Claude either answers (loop ends) or asks for more tools (loop continues).

This loop — *model picks tool → we run it → feed result back → repeat* — **is what an
"agent" is.** There's no magic; it's this while-loop plus a good model.

---

## How to debug when something breaks

- **Server won't start / client hangs at startup:** run the server's tools directly
  with a tiny script (see the smoke test we ran) to isolate whether the bug is in the
  server or the client.
- **Garbled protocol / "unexpected token":** something `print()`ed to **stdout** in the
  server. Move it to stderr. stdout is reserved for JSON-RPC on stdio transport.
- **Claude never calls a tool:** improve the **docstring** — tell it *when* to use the
  tool. The description is the model's only clue.
- **"ANTHROPIC_API_KEY is not set":** copy `.env.example` to `.env` and add your key.
- **See the raw messages:** set `MCP` logging or print `tool_list` / `block` objects.

Next → `05_architect_level.md` (taking this to production and designing systems).

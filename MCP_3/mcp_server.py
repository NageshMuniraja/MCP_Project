"""
mcp_server.py
=============
A *real* MCP server built with the official MCP Python SDK (`FastMCP`).

This is the important difference from your earlier MCP_2 / MCP_GAMIL_TOOL projects:
those were FastAPI HTTP endpoints that you *called* "MCP". They worked, but they
did NOT speak the Model Context Protocol. This file speaks the actual protocol:

  - It talks JSON-RPC 2.0 (you never see it — the SDK handles it).
  - By default it runs over STDIO (standard input/output), so an MCP host like
    Claude Desktop or our client.py can launch it as a subprocess and talk to it.
  - It exposes the 3 MCP "primitives":
        TOOLS     -> actions the AI can DO            (add_note, delete_note, ...)
        RESOURCES -> data the AI can READ             (notes://all)
        PROMPTS   -> reusable prompt templates         (daily_review)

Run it directly to sanity-check it:   python mcp_server.py
But normally you don't run it by hand — the client/host launches it for you.
"""

from mcp.server.fastmcp import FastMCP

import storage  # our plain-Python notes logic (no MCP knowledge inside it)

# The name shows up in MCP host UIs (e.g. Claude Desktop's tool list).
mcp = FastMCP("notes-manager")


# ===========================================================================
# 1) TOOLS  — things the AI is allowed to DO (they can have side effects).
#
# The @mcp.tool() decorator turns a normal Python function into an MCP tool.
# Two things matter a LOT and the SDK reads them automatically:
#   - The TYPE HINTS  -> become the tool's input schema (so the AI knows the args).
#   - The DOCSTRING   -> becomes the tool's description (so the AI knows WHEN to use it).
# Write docstrings for the AI, not just for humans.
# ===========================================================================

@mcp.tool()
def add_note(title: str, content: str, tags: list[str] | None = None) -> dict:
    """Create a new note. Use this whenever the user wants to save, jot down,
    or remember something. 'tags' is an optional list of short labels."""
    return storage.add_note(title, content, tags)


@mcp.tool()
def list_notes() -> list[dict]:
    """List every saved note. Use this when the user asks what notes they have."""
    return storage.list_notes()


@mcp.tool()
def search_notes(query: str) -> list[dict]:
    """Search notes by keyword (matches title, content, and tags).
    Use this when the user is looking for a specific note or topic."""
    return storage.search_notes(query)


@mcp.tool()
def get_note(note_id: str) -> dict:
    """Fetch one full note by its id. Use after search/list to read details."""
    note = storage.get_note(note_id)
    if note is None:
        # Raising is fine: the SDK turns it into a proper MCP tool error
        # that the AI client can see and react to.
        raise ValueError(f"No note found with id '{note_id}'")
    return note


@mcp.tool()
def delete_note(note_id: str) -> str:
    """Delete a note by its id. Use only when the user clearly wants it removed."""
    deleted = storage.delete_note(note_id)
    if not deleted:
        raise ValueError(f"No note found with id '{note_id}'")
    return f"Deleted note '{note_id}'."


# ===========================================================================
# 2) RESOURCES — read-only data the AI (or host) can fetch by URI.
#
# Think of resources like files/endpoints the host can load into context.
# Tools = verbs (do something). Resources = nouns (here is some data).
# A resource should NOT have side effects.
# ===========================================================================

@mcp.resource("notes://all")
def all_notes_resource() -> str:
    """All notes as readable text. A host can load this straight into context."""
    notes = storage.list_notes()
    if not notes:
        return "There are no notes yet."
    lines = []
    for n in notes:
        tags = f"  [tags: {', '.join(n['tags'])}]" if n["tags"] else ""
        lines.append(f"- ({n['id']}) {n['title']}{tags}\n    {n['content']}")
    return "\n".join(lines)


@mcp.resource("notes://{note_id}")
def single_note_resource(note_id: str) -> str:
    """A single note as text, addressed by URI (e.g. notes://a1b2c3d4).
    This is a *templated* resource — the {note_id} part is filled in by the caller."""
    note = storage.get_note(note_id)
    if note is None:
        return f"No note found with id '{note_id}'."
    return f"{note['title']}\n\n{note['content']}\n\nTags: {', '.join(note['tags']) or '(none)'}"


# ===========================================================================
# 3) PROMPTS — reusable, parameterized prompt templates the host can offer
#    to the user (e.g. as a slash-command or button). The SERVER ships the
#    prompt wording; the user just picks it. Great for standardizing workflows.
# ===========================================================================

@mcp.prompt()
def daily_review(focus: str = "everything") -> str:
    """A prompt that asks the AI to review the user's notes and suggest next steps.
    'focus' lets the user narrow it down, e.g. focus='work'."""
    return (
        f"Please review my notes (focus on: {focus}). "
        "First call the list_notes tool to see them, then: "
        "1) group them into themes, "
        "2) highlight anything time-sensitive, and "
        "3) suggest 3 concrete next actions."
    )


# ---------------------------------------------------------------------------
# Entry point. mcp.run() starts the server. With no transport argument it uses
# STDIO, which is exactly what our client.py and Claude Desktop expect.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()

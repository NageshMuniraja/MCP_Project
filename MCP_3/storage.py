"""
storage.py
==========
Plain Python storage for notes. This file has NOTHING to do with MCP or AI.

Why keep it separate?
  - A good habit (and an "architect-level" one): your business logic should not
    know it is being served over MCP. Today it's MCP; tomorrow it could be a REST
    API, a CLI, or a Slack bot. Keep the core logic pure and reusable.
  - mcp_server.py will simply *wrap* these functions and expose them as MCP tools.

The notes are saved to a JSON file next to this script so data survives restarts.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# The JSON "database". Lives right next to this file.
DB_PATH = Path(__file__).parent / "notes_db.json"


def _now() -> str:
    """Current UTC time as an ISO-8601 string (good practice: always store UTC)."""
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict]:
    """Read all notes from disk. Returns an empty list if the file doesn't exist yet."""
    if not DB_PATH.exists():
        return []
    try:
        return json.loads(DB_PATH.read_text())
    except json.JSONDecodeError:
        # Corrupt or empty file -> behave as if there were no notes.
        return []


def _save(notes: list[dict]) -> None:
    """Write all notes back to disk (pretty-printed so you can open and read it)."""
    DB_PATH.write_text(json.dumps(notes, indent=2))


# ---------------------------------------------------------------------------
# Public functions. Each one is small, pure-ish, and easy to test on its own.
# ---------------------------------------------------------------------------

def add_note(title: str, content: str, tags: list[str] | None = None) -> dict:
    """Create a new note and return it (including its generated id)."""
    notes = _load()
    note = {
        "id": uuid.uuid4().hex[:8],   # short, human-friendly id
        "title": title,
        "content": content,
        "tags": tags or [],
        "created_at": _now(),
    }
    notes.append(note)
    _save(notes)
    return note


def list_notes() -> list[dict]:
    """Return every note (newest last, the order they were created)."""
    return _load()


def get_note(note_id: str) -> dict | None:
    """Return a single note by id, or None if it doesn't exist."""
    for note in _load():
        if note["id"] == note_id:
            return note
    return None


def search_notes(query: str) -> list[dict]:
    """Case-insensitive search across title, content, and tags."""
    q = query.lower().strip()
    results = []
    for note in _load():
        haystack = " ".join([
            note["title"],
            note["content"],
            " ".join(note["tags"]),
        ]).lower()
        if q in haystack:
            results.append(note)
    return results


def delete_note(note_id: str) -> bool:
    """Delete a note by id. Returns True if something was deleted."""
    notes = _load()
    remaining = [n for n in notes if n["id"] != note_id]
    if len(remaining) == len(notes):
        return False  # nothing matched
    _save(remaining)
    return True

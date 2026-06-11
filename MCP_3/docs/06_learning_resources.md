# 06 — Learning Resources (Videos, Courses, Docs)

A curated path to go deeper. I've marked each item with the level it fits.
**A note on links:** official docs/repos are stable URLs. For YouTube, video URLs
go stale fast, so I give you the **channel + exact search phrase** to find the current
best video instead of a link that might 404. Search the phrase on YouTube.

---

## ⭐ Official & authoritative (trust these first)

| Resource | What / why | Level |
|----------|-----------|-------|
| **modelcontextprotocol.io** | The official MCP site: intro, concepts, quickstarts | All |
| **modelcontextprotocol.io/specification** | The actual protocol spec (JSON-RPC methods, lifecycle, transports, auth). Read it once you've done the code walkthrough. | Practitioner → Architect |
| **github.com/modelcontextprotocol** | The org: `python-sdk`, `typescript-sdk`, `servers` (reference servers), `inspector` | All |
| **github.com/modelcontextprotocol/python-sdk** | The SDK you used. Its README + `examples/` folder are excellent. | Practitioner |
| **github.com/modelcontextprotocol/servers** | Reference servers (filesystem, git, fetch, etc.) — **read these to learn real patterns.** | Practitioner → Architect |
| **Anthropic docs → "Model Context Protocol"** (docs.anthropic.com) | MCP from the host side, connecting servers to Claude | All |
| **Anthropic's MCP announcement (Nov 2024)** | The "why we built this" post. Good for the M×N framing. | Beginner |

## 🔧 Tools that make learning faster

- **MCP Inspector** (`npx @modelcontextprotocol/inspector`) — a GUI that connects to
  your server, lists tools/resources/prompts, and lets you call them by hand. **Run it
  against your `mcp_server.py`** — it's the fastest way to see your server from the
  outside without writing a client. Highly recommended next step.
- **Claude Desktop** — install it and wire up your server (see `05_architect_level.md`).
- **Claude Code** (`claude mcp add ...`) — add MCP servers to the coding agent.

## ▶️ YouTube (search these phrases on the channel)

> Tip: sort YouTube by date when the topic is fast-moving like MCP.

| Search this phrase | Channel to prefer | Level |
|--------------------|-------------------|-------|
| `Model Context Protocol explained` | **Anthropic** (official) | Beginner |
| `MCP Model Context Protocol crash course` | **Fireship** / **freeCodeCamp** | Beginner |
| `build MCP server python tutorial` | **Tech With Tim**, **freeCodeCamp** | Practitioner |
| `MCP server from scratch` | **ColeMedin**, **AI Jason** | Practitioner |
| `Model Context Protocol deep dive architecture` | **Anthropic**, **IBM Technology** | Architect |
| `MCP security prompt injection` | **IBM Technology**, security channels | Architect |
| `MCP vs function calling vs API` | general AI-eng channels | Beginner → Practitioner |

Reliable channels for this topic generally: **Anthropic**, **IBM Technology**
(great clear explainers), **freeCodeCamp** (long tutorials), **Fireship** (fast
overviews), **Tech With Tim** and **ColeMedin** (hands-on Python builds).

## 📚 Courses & written deep-dives

- **Anthropic's own MCP course / quickstart** (linked from modelcontextprotocol.io) —
  start here; it matches the SDK you used.
- **DeepLearning.AI short courses** — search their catalog for MCP / "MCP: Build Rich-
  Context AI Apps with Anthropic". Short, hands-on, free to audit. *(Practitioner)*
- **The spec, read end-to-end, once** — genuinely the best "architect" resource. It's
  shorter than you expect and removes all mystery. *(Architect)*

## 🗺️ A 3-week self-study plan (concrete)

**Week 1 — Foundations (Beginner → Practitioner)**
- Read docs `01`–`04` here; run this project; chat with your notes.
- Run **MCP Inspector** against `mcp_server.py`.
- Watch one "MCP explained" + one "build a Python MCP server" video.
- Exercise: add `edit_note` and a `notes://tags` resource.

**Week 2 — Build & connect (Practitioner)**
- Migrate your `MCP_GAMIL_TOOL` to a real MCP server (doc `03` shows how).
- Wire both servers into **Claude Desktop**.
- Read the official `servers` repo (filesystem + fetch servers) for patterns.
- Skim the spec sections on lifecycle, tools, resources, prompts.

**Week 3 — Architect (Architect)**
- Read doc `05` fully; read the spec's **transports** and **authorization** sections.
- Convert one server to **Streamable HTTP** and add a simple token check.
- Do the capstone exercise in doc `05`.
- Write a one-page design: "If my company wanted AI to safely access our CRM via MCP,
  here's the architecture, the transport, the auth, and the security controls." If you
  can write that page convincingly, you've hit architect level. 🎯

## How to verify anything you read

MCP moves fast and some blog posts are already outdated (e.g. they describe the old
HTTP+SSE transport). When in doubt, **the spec and the official SDK README win.**
Check the spec's version date at the top of the page.

---

That's the full path. Come back to `00_START_HERE.md` any time for the map.
When you're ready for a more complex project, we'll build on exactly these foundations.

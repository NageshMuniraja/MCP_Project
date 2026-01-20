# Gmail MCP Tool

This folder provides a small MCP (Model Context Protocol) server and client that let an LLM call Gmail helper tools via HTTP endpoints. The LLM chooses a tool (get_unread_emails, search_emails, get_email_full) and the client forwards tool output back to the LLM to produce final answers.

Contents
- `mcp_server.py` - FastAPI application exposing /tools/* endpoints backed by `gmail_tools.py`.
- `gmail_tools.py` - Helper functions that call the Gmail API: list unread messages, search messages, and fetch full message content (including short previews for attachments).
- `gmail_auth.py` - OAuth2 flow and helper to obtain an authorized Gmail API service object (used by the tools).
- `client.py` - Example client that asks the LLM what action to take, calls the MCP server, and then asks the LLM to summarize the result.

Setup
1. Create a virtual environment and install dependencies (recommended):

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Create a `.env` file in the workspace root with your OpenAI API key:

   OPENAI_API_KEY=sk-...your_key_here

3. Configure OAuth credentials for Gmail and place the credentials file as required by `gmail_auth.py` (usually `credentials.json`). Follow Google's OAuth setup steps if you haven't already.

Running the MCP server

Start the FastAPI server from this folder (reloader recommended during development):

   uvicorn mcp_server:app --reload --port 8000

The server exposes these endpoints:
- POST /tools/get_unread_emails
  - Request body: none (optional JSON {"max_results": n})
  - Response: {"count": n, "emails": [{id, threadId, headers, snippet}, ...]}

- POST /tools/search_emails
  - Request body: {"query": "from:someone@example.com", "max_results": 10}
  - Response: {"count": n, "results": [{id, threadId, headers, snippet}, ...]}

- POST /tools/get_email_full
  - Request body: {"message_id": "..."}
  - Response: {id, threadId, headers, body, attachments, snippet}

Client usage

Run the example client to ask natural language questions about your mailbox. The client will consult the LLM to decide which tool to call, call it on your behalf, and then ask the LLM to summarize the result.

- Interactive mode:

   python client.py

- Single-shot question:

   python client.py "Do I have any unread emails?"

- Piped question:

   echo "Show me mails from alice@example.com" | python client.py

Troubleshooting

- 404 from the client: make sure `mcp_server.py` is running and that you restarted it after adding endpoints.
- 422 from the server: check the request body shape. `search_emails` expects JSON {"query": ..., "max_results": ...}.
- No OPENAI_API_KEY: create a `.env` file or export the variable before launching the client.

Security and privacy

This project makes your Gmail content available to the LLM and to anything that can reach the running MCP server. Only run this locally and protect your credentials. Remove or secure the MCP server when not in use.

Extensions

- Add caching for message fetches to reduce Gmail API calls.
- Persist attachments to disk and point the LLM at saved files instead of inlining previews.
- Add more granular endpoints (mark-as-read, delete, reply, etc.) with careful consent and safety checks.

License

Use at your own risk.
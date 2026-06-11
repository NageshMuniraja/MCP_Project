"""
client.py
=========
An AI client that connects to our MCP server (mcp_server.py) over the REAL MCP
protocol and lets Claude use the notes tools by itself.

The big mental model — there are THREE roles in MCP:

    HOST    = the AI app the human talks to.      (this file is a tiny host)
    CLIENT  = the connector inside the host that  (the `ClientSession` below)
              speaks MCP to exactly one server.
    SERVER  = exposes tools/resources/prompts.    (mcp_server.py)

The flow this script runs:
    1. Launch mcp_server.py as a subprocess and open an MCP session over stdio.
    2. Ask the server "what tools do you have?" (session.list_tools()).
    3. Hand those tools to Claude.
    4. Claude reads the user's message and decides whether to call a tool.
    5. If it does, WE run the call against the MCP server and feed the result back.
    6. Repeat until Claude has a final text answer. (This loop = an "agent".)

Run:  python client.py        (needs ANTHROPIC_API_KEY in your environment / .env)
"""

import asyncio
import os

from anthropic import Anthropic

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load ANTHROPIC_API_KEY from a .env file if python-dotenv is installed.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODEL = "claude-sonnet-4-5"  # any current Claude model works; Sonnet is a good default

# Tells the MCP library HOW to start our server: just run it with python.
SERVER_PARAMS = StdioServerParameters(
    command="python",
    args=["mcp_server.py"],
)


def mcp_tools_to_anthropic(mcp_tools) -> list[dict]:
    """Convert MCP's tool definitions into the shape Anthropic's API expects.

    MCP and Anthropic both describe tools with a name + description + JSON schema,
    but the field names differ slightly. This adapter is the only 'glue'.
    """
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,  # MCP already gives us a JSON schema
        }
        for tool in mcp_tools
    ]


async def chat_once(anthropic: Anthropic, session: ClientSession, tools: list[dict], user_text: str):
    """Run ONE user turn through Claude, executing any tool calls it requests."""
    messages = [{"role": "user", "content": user_text}]

    # Agent loop: keep going while Claude wants to use tools.
    while True:
        response = anthropic.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=messages,
            tools=tools,
        )

        # Print any text Claude wrote this round.
        for block in response.content:
            if block.type == "text":
                print(f"\nClaude: {block.text}")

        # If Claude is done (no tool requested), we're finished with this turn.
        if response.stop_reason != "tool_use":
            return

        # Otherwise, run each tool Claude asked for, against the MCP server.
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"  -> Claude is calling MCP tool: {block.name}({block.input})")

            # THIS is the actual MCP call. The SDK sends JSON-RPC to the server.
            result = await session.call_tool(block.name, block.input or {})

            # result.content is a list of content blocks; join their text out.
            text = "".join(getattr(c, "text", "") for c in result.content)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": text,
            })

        # Send the tool outputs back so Claude can use them in its next reply.
        messages.append({"role": "user", "content": tool_results})


async def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set.\n"
            "Create MCP_3/.env with:  ANTHROPIC_API_KEY=sk-ant-...\n"
            "(copy .env.example to .env and fill it in)"
        )

    anthropic = Anthropic()

    # 1) Start the server subprocess and open the stdio transport.
    async with stdio_client(SERVER_PARAMS) as (read, write):
        # 2) Wrap the transport in an MCP session.
        async with ClientSession(read, write) as session:
            # 3) MCP handshake (capability negotiation). Always required.
            await session.initialize()

            # 4) Discover what the server offers.
            tool_list = (await session.list_tools()).tools
            tools = mcp_tools_to_anthropic(tool_list)
            print("Connected to MCP server 'notes-manager'.")
            print("Tools discovered:", ", ".join(t["name"] for t in tools))
            print("\nTry: 'Add a note titled Groceries: buy milk and eggs, tag it shopping'")
            print("Then: 'What notes do I have?'  or  'Search my notes for milk'")
            print("Type 'exit' to quit.\n")

            # 5) Simple REPL so you can chat with your notes.
            while True:
                try:
                    user_text = input("You> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nBye!")
                    break
                if user_text.lower() in {"exit", "quit"}:
                    break
                if not user_text:
                    continue
                await chat_once(anthropic, session, tools, user_text)


if __name__ == "__main__":
    asyncio.run(main())

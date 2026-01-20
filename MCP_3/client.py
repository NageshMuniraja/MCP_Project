import os
import json
import requests
from openai import OpenAI

# Load .env into environment if python-dotenv is installed so OPENAI_API_KEY in .env is picked up
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY not set. Install python-dotenv and add a .env file with OPENAI_API_KEY=sk-... or export the variable in your shell."
    )

client = OpenAI(api_key=api_key)

MCP_BASE = "http://localhost:8000/tools"

TOOL_DESCRIPTORS = [
    {
        "type": "function",
        "function": {
            "name": "get_unread_emails",
            "description": "Return a short list of unread emails (id, headers, snippet).",
            "parameters": {"type": "object", "properties": {"max_results": {"type": "integer"}}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_emails",
            "description": "Search emails using Gmail query language. Parameters: query (string), max_results (int).",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_email_full",
            "description": "Return full email content (body + attachments preview) for a given message id.",
            "parameters": {"type": "object", "properties": {"message_id": {"type": "string"}}}
        }
    }
]


def ask_llm(question: str):
    print(f"\nUser: {question}")

    # Ask the LLM whether a tool is required and which one
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that can call tools to access the user's Gmail. "
                    "If you need email data to answer, call exactly one of the available tools: "
                    "get_unread_emails, search_emails, or get_email_full."
                )
            },
            {"role": "user", "content": question}
        ],
        tools=TOOL_DESCRIPTORS,
        max_tokens=1000
    )

    message = response.choices[0].message

    # If the model decided to call a tool, perform the request to the MCP server and then summarize
    if getattr(message, "tool_calls", None):
        tool_call = message.tool_calls[0]

        # Robustly extract tool name and raw arguments since different SDK versions
        # may expose different attributes on the tool_call object.
        tool_name = None
        raw_args = None
        tc_dict = {}

        # Try to get a raw dict representation first (pydantic objects may support model_dump/dict)
        try:
            if hasattr(tool_call, "model_dump"):
                tc_dict = tool_call.model_dump()
            elif hasattr(tool_call, "dict"):
                tc_dict = tool_call.dict()
            else:
                try:
                    tc_dict = dict(tool_call)
                except Exception:
                    tc_dict = {}
        except Exception:
            tc_dict = {}

        # Try common attribute names on the tool_call object
        for attr in ("name", "tool", "function", "tool_name"):
            val = getattr(tool_call, attr, None)
            if val:
                tool_name = val
                break

        raw_args = getattr(tool_call, "arguments", None) or getattr(tool_call, "args", None)

        # Prefer values from the dict/model_dump when available (avoids getting a repr like "Function(...)")
        try:
            dict_name = tc_dict.get("name") or tc_dict.get("tool") or (tc_dict.get("function") if isinstance(tc_dict.get("function"), str) else None)
            dict_args = tc_dict.get("arguments") or tc_dict.get("args") or tc_dict.get("arguments_json")
            if dict_name:
                tool_name = dict_name
            if dict_args is not None and raw_args is None:
                raw_args = dict_args
        except Exception:
            pass

        # If tool_name is nested (object/dict), try to extract inner name
        if isinstance(tool_name, dict):
            tool_name = tool_name.get("name") or tool_name.get("tool")
        elif tool_name is not None and not isinstance(tool_name, str):
            # object with attribute 'name' or convertible to dict
            name_attr = getattr(tool_name, "name", None)
            if name_attr:
                tool_name = name_attr
            else:
                try:
                    if hasattr(tool_name, "model_dump"):
                        tcd = tool_name.model_dump()
                    elif hasattr(tool_name, "dict"):
                        tcd = tool_name.dict()
                    else:
                        tcd = dict(tool_name)
                    tool_name = tcd.get("name") or tcd.get("tool") or str(tool_name)
                except Exception:
                    tool_name = str(tool_name)

        # If raw_args is an object, try to convert to dict or string; if missing, read from tc_dict
        if raw_args is None:
            raw_args = tc_dict.get("arguments") or tc_dict.get("args") or tc_dict.get("arguments_json")
        elif raw_args is not None and not isinstance(raw_args, (str, dict, list)):
            try:
                if hasattr(raw_args, "model_dump"):
                    raw_args = raw_args.model_dump()
                elif hasattr(raw_args, "dict"):
                    raw_args = raw_args.dict()
                else:
                    raw_args = dict(raw_args)
            except Exception:
                raw_args = str(raw_args)

        # Final normalization: if tool_name still not a plain function name, try to parse from repr
        try:
            import re
            if isinstance(tool_name, str):
                # common reprs contain 'Function(... name='foo')' or "Function(name='foo', ...)"
                if re.search(r"\bFunction\(|\bfunction\(|\bToolCall\(|\bChatCompletion", tool_name):
                    m = re.search(r"name=[\'\"]?([A-Za-z0-9_\-]+)[\'\"]?", tool_name)
                    if m:
                        tool_name = m.group(1)
                    else:
                        # fallback: look for the last identifier-like token
                        m2 = re.search(r"([A-Za-z0-9_\-]+)\)\s*$", tool_name)
                        if m2:
                            tool_name = m2.group(1)
            else:
                rep = str(tool_name)
                m = re.search(r"\bname=[\'\"]?([A-Za-z0-9_\-]+)", rep)
                if m:
                    tool_name = m.group(1)
                else:
                    tool_name = rep
        except Exception:
            try:
                tool_name = str(tool_name)
            except Exception:
                tool_name = None

        # Ensure sane defaults
        if not tool_name:
            print("Could not determine tool name from LLM response.")
            return

        # arguments might be a JSON string
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        except Exception:
            args = {}

        # If the LLM didn't provide arguments, build sensible defaults per tool.
        if not args:
            if tool_name == "search_emails":
                # Try to extract a sender using a simple "from <name>" pattern, otherwise use the whole question as query
                try:
                    import re
                    m = re.search(r"from\s+([\w\s\.\-@]+)", question, re.I)
                    if m:
                        sender = m.group(1).strip().strip('\"\'?.')
                        query = f'from:"{sender}"'
                    else:
                        query = question
                except Exception:
                    query = question
                args = {"query": query, "max_results": 5}
            elif tool_name == "get_unread_emails":
                args = {"max_results": 5}
            elif tool_name == "get_email_full":
                # get_email_full requires a message_id; we can't proceed without it
                print("Tool get_email_full requires a message_id. Please ask to open a specific email or search first.")
                return

        print(f"LLM decided to call MCP tool: {tool_name} with args={args}")

        # Map tool name to endpoint
        endpoint = f"{MCP_BASE}/{tool_name}"

        try:
            # POST JSON body when arguments provided, otherwise simple POST
            if args:
                resp = requests.post(endpoint, json=args)
            else:
                resp = requests.post(endpoint)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print("Error calling MCP tool:", e)
            return

        # Ask the LLM to answer the original question using the tool output
        final = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an assistant that answers the user's question using the provided tool output. Be concise and include summaries when appropriate."},
                {"role": "user", "content": f"User question: {question}"},
                {"role": "user", "content": f"Tool ({tool_name}) output:\n{json.dumps(data, indent=2)}"}
            ],
            max_tokens=1500
        )

        print("\nFinal Answer:")
        print(final.choices[0].message.content)
    else:
        # Model answered directly without calling tools
        print("LLM Answer:")
        print(message.content)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Ask questions about your Gmail using LLM + MCP tools")
    parser.add_argument("question", nargs="*", help="The question to ask (omit to enter interactive mode)")
    args = parser.parse_args()

    # If question provided on CLI, use it
    if args.question:
        q = " ".join(args.question)
        ask_llm(q)
        sys.exit(0)

    # If piped via stdin, read entire stdin as the question
    if not sys.stdin.isatty():
        q = sys.stdin.read().strip()
        if q:
            ask_llm(q)
        else:
            print("No question provided on stdin.")
        sys.exit(0)

    # Otherwise enter interactive prompt
    print("Entering interactive mode. Type 'exit' or 'quit' to leave.")
    try:
        while True:
            q = input("\nQuestion> ").strip()
            if not q:
                continue
            if q.lower() in ("exit", "quit"):
                break
            ask_llm(q)
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")

# MCP Beginner Project – Employee Count

## What this project does
- Demonstrates MCP (Model Context Protocol) end to end
- LLM calls a tool instead of accessing data directly

## Architecture
User → LLM → MCP Tool → Data → MCP → LLM → User

## Steps to Run

### 1. Install dependencies
pip install -r requirements.txt

### 2. Start MCP server
uvicorn mcp_server:app --reload

### 3. Run client
python client.py

## Output
There are 120 employees.

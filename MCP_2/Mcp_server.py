from fastapi import FastAPI

app = FastAPI()

@app.post("/tools/get_employee_count")
def get_employee_count():
    """
    MCP TOOL:
    Returns total employee count.
    In real projects, this will query DB / API.
    """
    return {
        "employee_count": 120
    }

import requests

def ask_llm(question):
    print(f"\nUser Question: {question}")

    print("LLM: I need data. Calling MCP tool...")

    response = requests.post(
        "http://localhost:8000/tools/get_employee_count"
    )

    data = response.json()

    print(f"LLM Answer: There are {data['employee_count']} employees.")

if __name__ == "__main__":
    ask_llm("What is the employee count?")

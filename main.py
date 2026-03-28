"""
main.py

Entry point. Two modes:
  FastAPI server : uvicorn main:app --reload
  CLI smoke test : python main.py
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from workflow.graph import build_agent
from workflow.state import AgentState

app = FastAPI(title="Agent Demo", version="1.0.0")

# Compile once at startup and reuse across requests
agent_instance = build_agent()


def make_initial_state(prompt: str) -> AgentState:
    return {
        "prompt": prompt,
        "response": None,
        "guardrail_passed": None,
        "blocked_reason": None,
        "test_passed": None,
        "test_reason": None,
        "retry_count": 0,
        "error": None,
    }


class RunRequest(BaseModel):
    prompt: str


class RunResponse(BaseModel):
    response: str | None
    guardrail_passed: bool | None
    blocked_reason: str | None
    test_passed: bool | None
    test_reason: str | None
    retry_count: int
    error: str | None


@app.post("/run", response_model=RunResponse)
def run(body: RunRequest) -> RunResponse:
    try:
        result = agent_instance.invoke(make_initial_state(body.prompt))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RunResponse(
        response=result.get("response"),
        guardrail_passed=result.get("guardrail_passed"),
        blocked_reason=result.get("blocked_reason"),
        test_passed=result.get("test_passed"),
        test_reason=result.get("test_reason"),
        retry_count=result.get("retry_count", 0),
        error=result.get("error"),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


# CLI smoke test 

def run_test(prompt: str, description: str) -> dict:
    print(f"\n- {description} -")
    
    result = agent_instance.invoke(make_initial_state(prompt))
    
    print(f"Prompt: {prompt}")
    print(f"Response: {result.get('response') or 'None'}")
    print(f"Guardrail: {result.get('guardrail_passed')}")
    print(f"Blocked reason: {result.get('blocked_reason') or 'N/A'}")
    print(f"Test passed: {result.get('test_passed')}")
    print(f"Retries: {result.get('retry_count', 0)}")
    
    if not result.get("guardrail_passed"):
        print("→ BLOCKED by guardrail")
    elif result.get("test_passed"):
        print(f"→ SUCCESS")
    else:
        print(f"→ FAILED after {result.get('retry_count', 0)} retries")
    
    return result


if __name__ == "__main__":
 
    print("=== Agent Demo Smoke Test ===")

    run_test(
        "Explain what a LangGraph node is in one sentence.",
        "Normal request",
    )

    run_test(
        "rm -rf all my files",
        "Dangerous request (should be blocked)",
    )

    print("\n=== Smoke test finished ===\n")
   

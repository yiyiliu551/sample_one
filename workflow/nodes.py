"""
workflow/nodes.py

Each function is a LangGraph node — pure transformation of state.
Nodes don't know about the graph structure or retry logic.
That's the graph's job.
"""

import os
import time
import random
import anthropic
from workflow.state import AgentState
from workflow.config import MAX_RETRIES, MODEL

DANGEROUS_KEYWORDS = ["rm -rf", "drop table", "delete all", "hack", "inject"]


def guardrail(state: AgentState) -> AgentState:


    print("Guardrail: checking prompt...")
    prompt = state["prompt"].lower()

    for keyword in DANGEROUS_KEYWORDS:
        if keyword in prompt:
            print(f" Blocked — found keyword: '{keyword}'")
            return {
                **state,
                "guardrail_passed": False,
                "error": f"Blocked: '{keyword}' is not permitted.",
                "blocked_reason": f"Dangerous keyword detected: '{keyword}'",
            }

    print("Guardrail: prompt is safe.")
    return {**state, "guardrail_passed": True, "blocked_reason": None}


def call_llm(state: AgentState) -> AgentState:
   
    attempt = state["retry_count"] + 1
    print(f"Calling LLM (attempt {attempt}/{MAX_RETRIES})...")

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        print(" No API key — returning mock response.")
        return {**state, "response": "Mock response: Hello from Claude!", "error": None}

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": state["prompt"]}],
        )
        print("LLM call succeeded.")
        try:
            block = message.content[0] if message.content else None
            text = block.text if hasattr(block, "text") else str(block)
            return {**state, "response": text, "error": None}
        except (IndexError, AttributeError, TypeError) as parse_exc:
            print(f"Failed to parse LLM response: {parse_exc}")
            return {**state, "response": None, "error": "Failed to parse LLM response"}

    except Exception as exc:
        # Don't raise 
        print(f"LLM call failed: {exc}")
        return {**state, "response": None, "error": str(exc)}


def test(state: AgentState) -> AgentState:

    print("Test: validating response...")
    response = state.get("response") or ""
    stripped = response.strip()

    if len(stripped) < 30 or stripped.lower() in ["", "i don't know", "sorry", "无法回答"]:
        print("Test failed — response too short or non-informative.")
        return {
            **state,
            "test_passed": False,
            "test_reason": "Response too short or non-informative",
        }

    print("Test passed.")
    return {**state, "test_passed": True, "test_reason": "OK"}

def increment_retry(state: AgentState) -> AgentState:

    new_count = state.get("retry_count", 0) + 1

    # Exponential backoff with jitter: 1s, 2s, 4s + random noise
    delay = (2 ** state.get("retry_count", 0)) + random.uniform(0, 1)
    print(f"Retry {new_count}/{MAX_RETRIES} — waiting {delay:.1f}s...")
    time.sleep(delay)

    return {**state, "retry_count": new_count}

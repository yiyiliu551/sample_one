"""
workflow/state.py

"""

from typing import TypedDict, Optional


class AgentState(TypedDict):
    prompt: str                        # User's input
    response: Optional[str]            # LLM response
    guardrail_passed: Optional[bool]   # True = safe, False = blocked
    blocked_reason: Optional[str]      # Why the request was blocked
    test_passed: Optional[bool]        # True = response looks valid
    test_reason: Optional[str]         # Why test passed or failed
    retry_count: int                   # How many times we've retried
    error: Optional[str]               # Last error message

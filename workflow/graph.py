"""
workflow/graph.py

Wires nodes into a LangGraph workflow.
Node logic lives in nodes.py — this file only defines flow and routing.

Graph topology:

    ┌───────────┐
    │ guardrail │
    └─────┬─────┘
  blocked │ safe
    ┌─────┘ │
    │  ┌────▼──────┐
    │  │ call_llm  │◄──────────────────┐
    │  └────┬──────┘                   │
    │  ┌────▼──┐                       │
    │  │  test │                       │
    │  └────┬──┘                       │
    │  pass │ fail              ┌──────┴────────┐
    │  ┌────┘  └───────────────►│increment_retry│
    │  │                        └───────────────┘
    ▼  ▼
   END
"""

from langgraph.graph import StateGraph, END
from workflow.state import AgentState
from workflow.nodes import guardrail, call_llm, test, increment_retry
from workflow.config import MAX_RETRIES


def route_guardrail(state: AgentState) -> str:

    return "safe" if state.get("guardrail_passed") else "blocked"


def route_test(state: AgentState) -> str:
    
    if state.get("test_passed"):
        return "done"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        print(f" Max retries ({MAX_RETRIES}) reached.")
        return "done"
    return "retry"


def build_agent() -> StateGraph:
   
    workflow = StateGraph(AgentState)

    workflow.add_node("guardrail", guardrail)
    workflow.add_node("call_llm", call_llm)
    workflow.add_node("test", test)
    workflow.add_node("increment_retry", increment_retry)

    workflow.set_entry_point("guardrail")

    workflow.add_conditional_edges(
        "guardrail", route_guardrail,
        {"safe": "call_llm", "blocked": END},
    )
    workflow.add_edge("call_llm", "test")
    workflow.add_conditional_edges(
        "test", route_test,
        {"done": END, "retry": "increment_retry"},
    )
    workflow.add_edge("increment_retry", "call_llm")

    return workflow.compile()

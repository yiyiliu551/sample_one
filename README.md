# sample_one

# Agent Orchestration — System Design Notes

---

## 1. How the demo works

```
    ┌───────────┐
    │ guardrail │
    └─────┬─────┘
 blocked  │  safe
    ┌─────┘  │
    │  ┌─────▼─────┐
    │  │ call_llm  │◄──────────────────┐
    │  └─────┬─────┘                   │
    │  ┌─────▼──┐                      │
    │  │  test  │                      │
    │  └─────┬──┘                      │
    │  pass  │  fail           ┌───────┴────────┐
    │  ┌─────┘  └─────────────►│increment_retry │
    │  │                       └────────────────┘
    ▼  ▼
   END
```

**Nodes:**
- `guardrail` — keyword check, blocks bad requests before touching the LLM
- `call_llm` — calls Claude, stores failures in state instead of raising
- `test` — checks response quality, triggers retry if it fails
- `increment_retry` — bumps the counter and loops back

The graph and node logic are kept separate on purpose. Adding a new node
means writing a function in nodes.py and wiring it in graph.py — nothing else changes.

---

## 2. Reliability

**Timeout** — each node has a deadline. One slow node shouldn't block everything else.

**Circuit Breaker** — if the LLM API keeps failing, stop hammering it and switch to a fallback.

**Exponential Backoff** — wait longer between retries, not shorter. Doubling the delay
each time is the standard way to avoid making an overloaded service worse.

**Errors go into state, not exceptions** — lets the graph decide what to do next.
Nodes stay simple and testable.

---

## 3. Extensibility

Four layers, each with one job:
- `nodes.py` — business logic only, no idea how the graph is wired
- `graph.py` — routing and flow, no business logic
- `config.py` — all tunable parameters in one place
- `services/` — external calls, swap the LLM without touching anything else

Where this goes in production: the current design is an execution layer.
A real system would add a policy layer on top — deciding which model to use,
whether to hit RAG, which retrieval strategy to apply. Those decisions shouldn't
be hardcoded in nodes, they should be driven by the business context at runtime.

---

## 4. Observability

**Structured logging** — every log line is JSON with a `request_id`.
That one field lets you trace a request across every node it touched.

**Metrics** — Prometheus collects per-node latency, success rate, retry count.

**Dashboards** — Grafana pulls in both Prometheus metrics and Loki logs.
When something spikes in the metrics, you jump straight to the logs for that time window.
Filter by node to find the slow one, filter by request_id to see the full chain.

**Alerting** — AlertManager fires when failure rate crosses a threshold.
The goal is to know something's going wrong before users notice.

---

## 5. What's missing

**Retry is naive** — fixed count with backoff works for now, but production
needs smarter logic: different strategies for transient vs permanent failures.

**Test node is a heuristic** — checking response length catches obvious failures.
In production you'd want an LLM-as-judge scoring the output on multiple dimensions.

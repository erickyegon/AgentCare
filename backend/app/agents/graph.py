"""LangGraph orchestration — wires the six agents into a state machine.

Flow:

    START → coordinator → safety ─(safe)→ routing ─(resolved)→ appointment
                              │                 │
                          (halt)│           (uncertain)│
                              ▼                 ▼
                           finalize ◄───────────┘
    appointment → document → followup → finalize → END

Conditional edges implement the safety boundary (hard-stop on emergency/self-harm) and the
routing-uncertainty escalation. Every node persists its own state + step to SQL.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    appointment_node,
    coordinator_node,
    document_node,
    finalize_node,
    followup_node,
    routing_node,
    safety_node,
)
from app.agents.state import WorkflowState


# Node ids are suffixed so they never collide with WorkflowState keys
# (LangGraph forbids a node id equal to a state key such as "safety"/"routing").
COORDINATOR = "coordinator"
SAFETY = "safety_agent"
ROUTING = "routing_agent"
APPOINTMENT = "appointment_agent"
DOCUMENT = "document_agent"
FOLLOWUP = "followup_agent"
FINALIZE = "finalize"


def coordinator_router(state: WorkflowState) -> str:
    return FINALIZE if state.get("error") else SAFETY


def routing_router(state: WorkflowState) -> str:
    return FINALIZE if state.get("halted") else APPOINTMENT


def _safety_router(state: WorkflowState) -> str:
    return FINALIZE if state.get("halted") else ROUTING


def build_graph():
    g = StateGraph(WorkflowState)
    g.add_node(COORDINATOR, coordinator_node)
    g.add_node(SAFETY, safety_node)
    g.add_node(ROUTING, routing_node)
    g.add_node(APPOINTMENT, appointment_node)
    g.add_node(DOCUMENT, document_node)
    g.add_node(FOLLOWUP, followup_node)
    g.add_node(FINALIZE, finalize_node)

    g.add_edge(START, COORDINATOR)
    g.add_conditional_edges(COORDINATOR, coordinator_router,
                            {SAFETY: SAFETY, FINALIZE: FINALIZE})
    g.add_conditional_edges(SAFETY, _safety_router,
                            {ROUTING: ROUTING, FINALIZE: FINALIZE})
    g.add_conditional_edges(ROUTING, routing_router,
                            {APPOINTMENT: APPOINTMENT, FINALIZE: FINALIZE})
    g.add_edge(APPOINTMENT, DOCUMENT)
    g.add_edge(DOCUMENT, FOLLOWUP)
    g.add_edge(FOLLOWUP, FINALIZE)
    g.add_edge(FINALIZE, END)
    return g.compile()


@lru_cache(maxsize=1)
def get_graph():
    """Compile the graph once and reuse it."""
    return build_graph()

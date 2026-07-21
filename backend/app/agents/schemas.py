"""Structured decision schemas produced by the LLM (or the deterministic mock).

Using structured output keeps agent decisions machine-checkable and auditable — the LLM
returns a validated object, never free-form text that gets regex-parsed.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IntentType = Literal[
    "book_appointment",
    "reschedule_appointment",
    "cancel_appointment",
    "document_submission",
    "follow_up",
    "general_inquiry",
    "emergency",
    "clinical_advice_request",
]

SafetyCategory = Literal["none", "emergency", "clinical_advice", "self_harm", "sensitive"]


class IntentDecision(BaseModel):
    """Administrative intent extracted from the patient's request."""

    primary_intent: IntentType = Field(description="The dominant administrative intent.")
    wants_appointment: bool = False
    wants_reschedule: bool = False
    wants_cancel: bool = False
    involves_documents: bool = False
    requested_specialty: str | None = Field(
        default=None, description="Free-text specialty/department the patient mentioned, if any."
    )
    timeframe: str | None = Field(
        default=None, description="Any timing the patient mentioned, e.g. 'next week'."
    )
    summary: str = Field(description="One-sentence neutral, administrative restatement.")


class SafetyDecision(BaseModel):
    """Safety classification. NEVER contains diagnosis or treatment content."""

    category: SafetyCategory = "none"
    is_safe: bool = True
    requires_stop: bool = Field(
        default=False,
        description="True if automated administrative actions must halt (emergency/self-harm).",
    )
    requires_human: bool = Field(
        default=False, description="True if a human must review before/after proceeding."
    )
    severity: Literal["low", "medium", "high", "critical"] = "low"
    reason: str = Field(description="Why this classification was chosen (administrative language).")
    patient_message: str = Field(
        default="",
        description="Safe, administrative message for the patient. No medical advice.",
    )


class RoutingDecision(BaseModel):
    """Department routing proposal (validated against the DB catalog afterwards)."""

    department_label: str = Field(description="Best-match department name or slug from the catalog.")
    confidence: float = Field(ge=0.0, le=1.0)
    is_supported: bool = Field(
        default=True, description="False if no listed department reasonably fits the request."
    )
    rationale: str = Field(description="Administrative reason for this routing.")

"""Deterministic, input-driven decision logic.

These functions back the ``MockLLM`` and serve as the graceful-degradation fallback for the
real provider. They are genuine logic over the request text — the same input always yields the
same structured decision, and different inputs yield different decisions.
"""

from __future__ import annotations

import re

from app.agents.schemas import IntentDecision, RoutingDecision, SafetyDecision

# ---- Safety signals -------------------------------------------------------------------

_EMERGENCY = re.compile(
    r"\b(chest pain|can'?t breathe|cannot breathe|difficulty breathing|shortness of breath|"
    r"heart attack|stroke|unconscious|passed out|severe bleeding|bleeding heavily|"
    r"suicidal thoughts|overdose|seizure|anaphyla|choking|not breathing)\b",
    re.I,
)
_SELF_HARM = re.compile(
    r"\b(kill myself|suicide|suicidal|end my life|self[-\s]?harm|hurt myself)\b", re.I
)
_CLINICAL_ADVICE = re.compile(
    r"\b(diagnos|what'?s wrong with me|what is wrong with me|what medication|which medicine|"
    r"what dose|dosage|prescrib|should i take|is it (cancer|serious)|interpret (my|the) (result|report)|"
    r"what does (my|this) (result|report|ecg|scan) mean)\b",
    re.I,
)


def assess_safety(text: str) -> SafetyDecision:
    t = text or ""
    if _SELF_HARM.search(t):
        return SafetyDecision(
            category="self_harm",
            is_safe=False,
            requires_stop=True,
            requires_human=True,
            severity="critical",
            reason="Language indicating possible self-harm was detected; human support required.",
            patient_message=(
                "It sounds like you may be going through a very difficult time. AgentCare cannot "
                "help with this directly, but please reach out to a local crisis line or emergency "
                "services right now — you deserve immediate support from a person."
            ),
        )
    if _EMERGENCY.search(t):
        return SafetyDecision(
            category="emergency",
            is_safe=False,
            requires_stop=True,
            requires_human=True,
            severity="critical",
            reason="Possible medical emergency detected in the request wording.",
            patient_message=(
                "This may be a medical emergency. Please contact your local emergency number or go "
                "to the nearest emergency department immediately. AgentCare handles administrative "
                "coordination only and cannot manage urgent medical situations."
            ),
        )
    if _CLINICAL_ADVICE.search(t):
        return SafetyDecision(
            category="clinical_advice",
            is_safe=True,  # the administrative parts may still proceed
            requires_stop=False,
            requires_human=True,
            severity="medium",
            reason="Request includes a clinical question that only a clinician may answer.",
            patient_message=(
                "I can help with administrative steps like booking and documents, but questions "
                "about diagnosis, results, or medication must be answered by a qualified clinician. "
                "I've flagged that part for the care team."
            ),
        )
    return SafetyDecision(
        category="none", is_safe=True, requires_stop=False, requires_human=False,
        severity="low", reason="No safety concerns detected; ordinary administrative request.",
    )


# ---- Intent signals -------------------------------------------------------------------

_RESCHEDULE = re.compile(r"\b(reschedul|move|change).{0,20}(appointment|booking|visit)\b", re.I)
_CANCEL = re.compile(r"\b(cancel|delete).{0,20}(appointment|booking|visit)\b", re.I)
_BOOK = re.compile(r"\b(book|schedule|need|want|make|set up|arrange).{0,30}"
                   r"(appointment|consultation|visit|follow[-\s]?up|check[-\s]?up|slot|see a doctor)\b", re.I)
_DOCS = re.compile(r"\b(attach|upload|document|report|ecg|scan|x[-\s]?ray|blood|referral|record)\b", re.I)
_FOLLOWUP = re.compile(r"\bfollow[-\s]?up\b", re.I)

# Specialty keyword -> canonical department label.
# Patterns anchor the start of a word but allow suffixes (so "neuro" matches "neurology").
_SPECIALTY_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(heart|cardio|ecg|ekg|chest|palpitation)", re.I), "Cardiology"),
    (re.compile(r"\b(bone|joint|fracture|ortho|knee|shoulder|spine|back pain)", re.I), "Orthopedics"),
    (re.compile(r"\b(skin|derma|rash|acne|mole)", re.I), "Dermatology"),
    (re.compile(r"\b(child|kid|paediatric|pediatric|infant|baby)", re.I), "Pediatrics"),
    (re.compile(r"\b(brain|neuro|migraine|headache|seizure|nerve)", re.I), "Neurology"),
    (re.compile(r"\b(eye|vision|ophthal|optometry)", re.I), "Ophthalmology"),
    (re.compile(r"\b(ear|nose|throat|ent|sinus|hearing)", re.I), "ENT"),
    (re.compile(r"\b(x[-\s]?ray|mri|ct scan|ultrasound|imaging|radiolog)", re.I), "Radiology"),
    (re.compile(r"\b(general|gp|family|physician|check[-\s]?up|fever|cold)", re.I), "General Medicine"),
]


def detect_specialty(text: str) -> str | None:
    for pattern, label in _SPECIALTY_MAP:
        if pattern.search(text or ""):
            return label
    return None


def _timeframe(text: str) -> str | None:
    m = re.search(r"\b(today|tomorrow|next week|this week|next month|in \d+ days?|on \w+day)\b",
                  text or "", re.I)
    return m.group(0) if m else None


def detect_intent(text: str) -> IntentDecision:
    t = text or ""
    specialty = detect_specialty(t)
    timeframe = _timeframe(t)
    involves_docs = bool(_DOCS.search(t))

    if _CANCEL.search(t):
        primary = "cancel_appointment"
    elif _RESCHEDULE.search(t):
        primary = "reschedule_appointment"
    elif _BOOK.search(t) or specialty:
        primary = "book_appointment"
    elif involves_docs:
        primary = "document_submission"
    elif _FOLLOWUP.search(t):
        primary = "follow_up"
    else:
        primary = "general_inquiry"

    return IntentDecision(
        primary_intent=primary,
        wants_appointment=primary in ("book_appointment", "follow_up") or bool(specialty),
        wants_reschedule=primary == "reschedule_appointment",
        wants_cancel=primary == "cancel_appointment",
        involves_documents=involves_docs,
        requested_specialty=specialty,
        timeframe=timeframe,
        summary=_intent_summary(primary, specialty, timeframe),
    )


def _intent_summary(primary: str, specialty: str | None, timeframe: str | None) -> str:
    dept = f" in {specialty}" if specialty else ""
    when = f" ({timeframe})" if timeframe else ""
    return {
        "book_appointment": f"Patient requests to book an appointment{dept}{when}.",
        "reschedule_appointment": "Patient requests to reschedule an existing appointment.",
        "cancel_appointment": "Patient requests to cancel an existing appointment.",
        "document_submission": "Patient wishes to submit or attach documents.",
        "follow_up": f"Patient requests a follow-up{dept}{when}.",
        "general_inquiry": "Patient has a general administrative inquiry.",
    }.get(primary, "Administrative request.")


def route_department(text: str, catalog: list[dict]) -> RoutingDecision:
    """Map to a catalog department using specialty detection + keyword overlap."""
    specialty = detect_specialty(text)
    names = {d["name"].lower(): d for d in catalog}
    if specialty and specialty.lower() in names:
        return RoutingDecision(
            department_label=specialty, confidence=0.9, is_supported=True,
            rationale=f"Request maps to {specialty} on administrative grounds.",
        )
    # Fall back to General Medicine if present.
    if "general medicine" in names:
        return RoutingDecision(
            department_label="General Medicine", confidence=0.5, is_supported=True,
            rationale="No specific specialty detected; routing to General Medicine for triage.",
        )
    if catalog:
        return RoutingDecision(
            department_label=catalog[0]["name"], confidence=0.3, is_supported=False,
            rationale="Could not confidently match a department.",
        )
    return RoutingDecision(
        department_label="", confidence=0.0, is_supported=False,
        rationale="No departments configured.",
    )

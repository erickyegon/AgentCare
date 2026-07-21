"""Document Agent — coordinate attached documents and check completeness.

Documents are uploaded and stored (checksum + classification + dedupe) before the workflow
runs; this agent reviews the attached set, summarizes types, counts duplicates, maps them to
the patient/workflow, and flags any missing required documents for the routed department.
"""

from __future__ import annotations

from collections import Counter

from app.agents.state import WorkflowState
from app.core.db import session_scope
from app.models import Department, PatientDocument, WorkflowStatus
from app.agents.nodes._common import persist_run_state, record_step
from app.tools import write_audit
from app.tools.document_tools import missing_required_documents

AGENT = "document_agent"


def document_node(state: WorkflowState) -> dict:
    run_id = state["run_id"]
    patient_id = state.get("patient_id")
    document_ids = state.get("document_ids", [])
    routing = state.get("routing", {})

    with session_scope() as db:
        docs: list[PatientDocument] = []
        if document_ids:
            docs = list(
                db.query(PatientDocument).filter(
                    PatientDocument.id.in_(document_ids),
                    PatientDocument.patient_id == patient_id,
                )
            )

        type_counts = Counter(d.document_type.value for d in docs)
        duplicates = sum(1 for d in docs if d.is_duplicate)

        # Missing-document check against the routed department's requirements.
        missing: list[str] = []
        dept_slug = None
        if routing.get("department_id"):
            dept = db.get(Department, routing["department_id"])
            if dept is not None:
                dept_slug = dept.slug
                missing = missing_required_documents(
                    db, patient_id=patient_id, department_slug=dept_slug
                )

        data = {
            "processed": True,
            "attached": len(docs),
            "stored": len(docs),
            "by_type": dict(type_counts),
            "duplicates": duplicates,
            "missing": missing,
            "document_ids": [d.id for d in docs],
        }

        if docs:
            msg = (
                f"Reviewed {len(docs)} attached document(s): "
                + ", ".join(f"{v}× {k}" for k, v in type_counts.items())
            )
            if duplicates:
                msg += f"; {duplicates} duplicate(s) flagged"
        else:
            msg = "No documents attached to this request."
        if missing:
            msg += f". Missing required for {dept_slug}: {', '.join(missing)}"

        write_audit(db, action="documents.coordinated", entity_type="workflow_run",
                    entity_id=run_id, actor=AGENT, workflow_run_id=run_id,
                    meta={"attached": len(docs), "duplicates": duplicates, "missing": missing})
        step = record_step(db, run_id=run_id, agent=AGENT, action="coordinate_documents",
                           message=msg, data=data)
        persist_run_state(db, run_id=run_id, state_patch={"documents": data},
                          current_step="followup", status=WorkflowStatus.RUNNING)
        db.commit()

    return {"documents": data, "current_step": "followup", "trace": [step]}

"""Department-lookup tool — resolve a routing label to a real, active department.

Real logic: queries active departments and matches by slug/name/keyword. The LLM
routing agent proposes a department label; this tool validates it against the DB so the
system can only route to departments that actually exist.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Department
from app.tools.base import ToolResult


def _tokenize(text: str) -> set[str]:
    return {t.strip().lower() for t in text.replace(",", " ").split() if t.strip()}


def lookup_department(db: Session, *, label: str) -> ToolResult:
    """Match a free-text department label to an active Department.

    Matching precedence: exact slug/name → substring on name → keyword overlap score.
    """
    label = (label or "").strip().lower()
    departments = list(db.scalars(select(Department).where(Department.active.is_(True))))
    if not departments:
        return ToolResult(ok=False, message="No active departments configured.")

    catalog = [
        {"id": d.id, "name": d.name, "slug": d.slug, "keywords": d.keywords} for d in departments
    ]

    # 1) Exact slug or name match.
    for d in departments:
        if label in (d.slug.lower(), d.name.lower()):
            return ToolResult(
                ok=True,
                message=f"Routed to {d.name}.",
                data={"department_id": d.id, "department_name": d.name, "match": "exact",
                      "confidence": 1.0, "catalog": catalog},
            )

    # 2) Substring match on name.
    for d in departments:
        if label and label in d.name.lower():
            return ToolResult(
                ok=True,
                message=f"Routed to {d.name} (name match).",
                data={"department_id": d.id, "department_name": d.name, "match": "substring",
                      "confidence": 0.8, "catalog": catalog},
            )

    # 3) Keyword-overlap scoring.
    label_tokens = _tokenize(label)
    best: tuple[float, Department] | None = None
    for d in departments:
        kw = _tokenize(d.keywords) | _tokenize(d.name)
        if not kw:
            continue
        overlap = len(label_tokens & kw)
        score = overlap / max(1, len(label_tokens or {""}))
        if overlap and (best is None or score > best[0]):
            best = (score, d)

    if best and best[0] > 0:
        score, d = best
        return ToolResult(
            ok=True,
            message=f"Routed to {d.name} (keyword match, score={score:.2f}).",
            data={"department_id": d.id, "department_name": d.name, "match": "keyword",
                  "confidence": round(min(0.75, 0.4 + score / 2), 2), "catalog": catalog},
        )

    return ToolResult(
        ok=False,
        message=f"Could not confidently map '{label}' to a department.",
        data={"match": "none", "confidence": 0.0, "catalog": catalog},
    )

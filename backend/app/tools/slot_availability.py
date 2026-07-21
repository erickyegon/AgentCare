"""Slot-availability tool — retrieve real, bookable appointment slots."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import AppointmentSlot, Doctor, SlotStatus
from app.tools.base import ToolResult


def find_available_slots(
    db: Session,
    *,
    department_id: int,
    after: datetime | None = None,
    before: datetime | None = None,
    limit: int = 10,
) -> ToolResult:
    """Return up-to ``limit`` available future slots for doctors in a department.

    Real logic: joins doctors → slots, filters to AVAILABLE and in the future, optionally
    within a [after, before] window, ordered by soonest.
    """
    now = datetime.now(timezone.utc)
    after = after or now

    conditions = [
        Doctor.department_id == department_id,
        Doctor.active.is_(True),
        AppointmentSlot.status == SlotStatus.AVAILABLE,
        AppointmentSlot.start_time >= after,
    ]
    if before is not None:
        conditions.append(AppointmentSlot.start_time <= before)

    stmt = (
        select(AppointmentSlot, Doctor)
        .join(Doctor, AppointmentSlot.doctor_id == Doctor.id)
        .where(and_(*conditions))
        .order_by(AppointmentSlot.start_time.asc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()

    slots = [
        {
            "slot_id": slot.id,
            "doctor_id": doctor.id,
            "doctor_name": doctor.name,
            "specialty": doctor.specialty,
            "start_time": slot.start_time.isoformat(),
            "end_time": slot.end_time.isoformat(),
        }
        for slot, doctor in rows
    ]

    if not slots:
        return ToolResult(
            ok=False,
            message="No available slots found for this department in the requested window.",
            data={"slots": [], "department_id": department_id},
        )
    return ToolResult(
        ok=True,
        message=f"Found {len(slots)} available slot(s).",
        data={"slots": slots, "department_id": department_id},
    )

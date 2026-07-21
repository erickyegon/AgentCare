"""Department, doctor, and slot routes (catalog).

Reads are available to any authenticated user; mutations require staff/admin.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_staff
from app.api.errors import NotFoundError
from app.core.db import get_db
from app.models import AppointmentSlot, Department, Doctor, SlotStatus, User
from app.schemas.catalog import (
    DepartmentCreate,
    DepartmentOut,
    DoctorCreate,
    DoctorOut,
    SlotCreate,
    SlotOut,
)
from app.tools import find_available_slots, write_audit

router = APIRouter(tags=["catalog"])


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Department]:
    return list(db.scalars(select(Department).where(Department.active.is_(True)).order_by(Department.name)))


@router.get("/departments/{department_id}/doctors", response_model=list[DoctorOut])
def list_doctors(
    department_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Doctor]:
    return list(
        db.scalars(
            select(Doctor).where(Doctor.department_id == department_id, Doctor.active.is_(True))
        )
    )


@router.get("/departments/{department_id}/slots", response_model=list[SlotOut])
def list_slots(
    department_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[AppointmentSlot]:
    result = find_available_slots(db, department_id=department_id, limit=50)
    slot_ids = [s["slot_id"] for s in result.data.get("slots", [])]
    if not slot_ids:
        return []
    return list(db.scalars(select(AppointmentSlot).where(AppointmentSlot.id.in_(slot_ids))))


# ---- Staff mutations ----------------------------------------------------------------


@router.post("/departments", response_model=DepartmentOut, status_code=201)
def create_department(
    payload: DepartmentCreate, db: Session = Depends(get_db), staff: User = Depends(require_staff)
) -> Department:
    dept = Department(
        name=payload.name, slug=_slugify(payload.name),
        description=payload.description, keywords=payload.keywords, active=True,
    )
    db.add(dept)
    write_audit(db, action="department.created", entity_type="department", actor="staff",
                actor_id=staff.id, meta={"name": payload.name})
    db.commit()
    db.refresh(dept)
    return dept


@router.post("/doctors", response_model=DoctorOut, status_code=201)
def create_doctor(
    payload: DoctorCreate, db: Session = Depends(get_db), staff: User = Depends(require_staff)
) -> Doctor:
    if db.get(Department, payload.department_id) is None:
        raise NotFoundError("Department not found")
    doctor = Doctor(
        department_id=payload.department_id, name=payload.name,
        specialty=payload.specialty, active=True,
    )
    db.add(doctor)
    write_audit(db, action="doctor.created", entity_type="doctor", actor="staff",
                actor_id=staff.id, meta={"name": payload.name})
    db.commit()
    db.refresh(doctor)
    return doctor


@router.post("/slots", response_model=SlotOut, status_code=201)
def create_slot(
    payload: SlotCreate, db: Session = Depends(get_db), staff: User = Depends(require_staff)
) -> AppointmentSlot:
    if db.get(Doctor, payload.doctor_id) is None:
        raise NotFoundError("Doctor not found")
    slot = AppointmentSlot(
        doctor_id=payload.doctor_id, start_time=payload.start_time,
        end_time=payload.end_time, status=SlotStatus.AVAILABLE,
    )
    db.add(slot)
    write_audit(db, action="slot.created", entity_type="appointment_slot", actor="staff",
                actor_id=staff.id, meta={"doctor_id": payload.doctor_id})
    db.commit()
    db.refresh(slot)
    return slot

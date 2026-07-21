"""Synthetic, anonymized seed data.

Everything here is fabricated for demonstration — no real patients, no real credentials.
The default account password comes from ``SEED_DEFAULT_PASSWORD`` (env), not hardcoded PII.
Running the seed is idempotent: existing rows (matched by natural keys) are reused.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import session_scope
from app.core.security import hash_password
from app.db.init_db import create_all
from app.models import (
    AppointmentSlot,
    Department,
    Doctor,
    PatientProfile,
    SlotStatus,
    User,
    UserRole,
)

logger = logging.getLogger("agentcare.seed")

DEPARTMENTS = [
    ("Cardiology", "cardiology", "Heart and cardiovascular administrative care.",
     "heart cardiac cardio ecg ekg chest palpitation cardiovascular follow-up"),
    ("Orthopedics", "orthopedics", "Bones, joints, and musculoskeletal coordination.",
     "bone joint fracture ortho knee shoulder spine back hip musculoskeletal"),
    ("Dermatology", "dermatology", "Skin-related appointments and documents.",
     "skin derma rash acne mole eczema dermatology"),
    ("Pediatrics", "pediatrics", "Children's health administration.",
     "child kid paediatric pediatric infant baby vaccination"),
    ("Neurology", "neurology", "Nervous-system appointment coordination.",
     "brain neuro migraine headache seizure nerve neurology"),
    ("Ophthalmology", "ophthalmology", "Eye-care appointments.",
     "eye vision ophthal optometry retina glaucoma"),
    ("ENT", "ent", "Ear, nose, and throat coordination.",
     "ear nose throat ent sinus hearing tonsil"),
    ("Radiology", "radiology", "Imaging appointment scheduling and reports.",
     "x-ray mri ct scan ultrasound imaging radiology"),
    ("General Medicine", "general-medicine", "General and family medicine triage.",
     "general gp family physician check-up fever cold triage"),
    ("Oncology", "oncology", "Oncology administrative coordination and follow-up.",
     "oncology cancer tumor chemotherapy follow-up"),
]

DOCTORS = {
    "cardiology": ["Dr. Amara Okafor", "Dr. Liam Chen", "Dr. Priya Nair"],
    "orthopedics": ["Dr. Sofia Rossi", "Dr. Kwame Mensah"],
    "dermatology": ["Dr. Hana Kim", "Dr. Diego Alvarez"],
    "pediatrics": ["Dr. Fatima Zahra", "Dr. Noah Bennett"],
    "neurology": ["Dr. Ingrid Larsson", "Dr. Rahul Verma"],
    "ophthalmology": ["Dr. Yuki Tanaka"],
    "ent": ["Dr. Omar Farouk"],
    "radiology": ["Dr. Elena Petrova"],
    "general-medicine": ["Dr. Grace Achieng", "Dr. Tom Whitfield", "Dr. Aisha Bello"],
    "oncology": ["Dr. Marcus Lindqvist"],
}

# Synthetic accounts. Passwords are the env default, never committed.
STAFF_USERS = [
    ("System Administrator", "admin@agentcare.io", UserRole.ADMIN),
    ("Nadia Coordinator", "staff@agentcare.io", UserRole.STAFF),
    ("Ben Frontdesk", "frontdesk@agentcare.io", UserRole.STAFF),
]
PATIENT_USERS = [
    ("Jane Patient", "patient@agentcare.io"),
    ("Carlos Mendez", "carlos@agentcare.io"),
    ("Mei Lin", "mei@agentcare.io"),
]


def _get_or_create_department(db: Session, name, slug, desc, keywords) -> Department:
    dept = db.scalar(select(Department).where(Department.slug == slug))
    if dept is None:
        dept = Department(name=name, slug=slug, description=desc, keywords=keywords, active=True)
        db.add(dept)
        db.flush()
    return dept


def _get_or_create_doctor(db: Session, dept: Department, name: str) -> Doctor:
    doc = db.scalar(
        select(Doctor).where(Doctor.department_id == dept.id, Doctor.name == name)
    )
    if doc is None:
        doc = Doctor(department_id=dept.id, name=name, specialty=dept.name, active=True)
        db.add(doc)
        db.flush()
    return doc


def _ensure_slots(db: Session, doctor: Doctor, days: int = 30) -> int:
    """Create available slots on business days for the next ``days`` days (idempotent)."""
    existing = db.scalar(
        select(func.count(AppointmentSlot.id)).where(AppointmentSlot.doctor_id == doctor.id)
    )
    if existing and existing > 0:
        return 0

    created = 0
    today = datetime.now(timezone.utc).date()
    hours = [9, 11, 14, 16]
    for d in range(1, days + 1):
        day = today + timedelta(days=d)
        if day.weekday() >= 5:  # skip weekends
            continue
        for h in hours:
            start = datetime.combine(day, time(hour=h), tzinfo=timezone.utc)
            slot = AppointmentSlot(
                doctor_id=doctor.id, start_time=start, end_time=start + timedelta(minutes=30),
                status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
            created += 1
    return created


def _get_or_create_user(db: Session, name, email, role) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(name=name, email=email, role=role,
                    password_hash=hash_password(settings.seed_default_password), is_active=True)
        db.add(user)
        db.flush()
    return user


def seed_all(create_tables: bool = True) -> dict:
    if create_tables:
        create_all()

    counts = {"departments": 0, "doctors": 0, "slots": 0, "users": 0, "patients": 0}
    with session_scope() as db:
        for name, slug, desc, keywords in DEPARTMENTS:
            dept = _get_or_create_department(db, name, slug, desc, keywords)
            counts["departments"] += 1
            for doc_name in DOCTORS.get(slug, []):
                doctor = _get_or_create_doctor(db, dept, doc_name)
                counts["doctors"] += 1
                counts["slots"] += _ensure_slots(db, doctor)

        for name, email, role in STAFF_USERS:
            _get_or_create_user(db, name, email, role)
            counts["users"] += 1

        for name, email in PATIENT_USERS:
            user = _get_or_create_user(db, name, email, UserRole.PATIENT)
            counts["users"] += 1
            if db.scalar(select(PatientProfile).where(PatientProfile.user_id == user.id)) is None:
                db.add(PatientProfile(user_id=user.id, preferred_language="English",
                                      phone="+10000000000"))
                counts["patients"] += 1

        db.commit()

    logger.info("Seed complete: %s", counts)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = seed_all()
    print("Seeded:", result)
    print(f"Demo login password (from env): {settings.seed_default_password}")
    print("Accounts: admin@agentcare.io / staff@agentcare.io / patient@agentcare.io")

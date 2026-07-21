"""Authentication & profile routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models import PatientProfile, User, UserRole
from app.schemas.auth import (
    LoginRequest,
    ProfileUpdate,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.tools import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Self-registration always creates a PATIENT account (staff are provisioned by admin/seed)."""
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.PATIENT,
    )
    db.add(user)
    db.flush()
    profile = PatientProfile(
        user_id=user.id,
        phone=payload.phone,
        date_of_birth=payload.date_of_birth,
        preferred_language=payload.preferred_language,
        emergency_contact=payload.emergency_contact,
    )
    db.add(profile)
    write_audit(db, action="user.registered", entity_type="user", entity_id=user.id,
                actor="patient", actor_id=user.id, meta={"role": user.role.value})
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, role=user.role, user_id=user.id, name=user.name)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, role=user.role, user_id=user.id, name=user.name)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if user.role != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients only")
    profile = db.scalar(select(PatientProfile).where(PatientProfile.user_id == user.id))
    if profile is None:
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(user)
    return user

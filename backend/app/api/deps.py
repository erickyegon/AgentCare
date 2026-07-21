"""FastAPI dependencies for authentication and role-based access control.

RBAC is enforced here, in backend code — routes declare the roles they require and, where
relevant, ownership is checked against the authenticated user. Hiding buttons in the UI is
never the access control.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.errors import ForbiddenError
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import PatientProfile, User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = decode_access_token(credentials.credentials)
    if claims is None or "sub" not in claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory enforcing that the caller holds one of ``roles``."""
    allowed = set(roles)

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise ForbiddenError(
                f"Requires role(s): {', '.join(r.value for r in allowed)}; "
                f"you are '{user.role.value}'."
            )
        return user

    return _checker


def require_staff(user: User = Depends(get_current_user)) -> User:
    """Staff or admin."""
    if user.role not in (UserRole.STAFF, UserRole.ADMIN):
        raise ForbiddenError("Staff or admin role required.")
    return user


def get_current_patient_profile(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PatientProfile:
    """Return the authenticated patient's profile, creating one on demand."""
    if user.role != UserRole.PATIENT:
        raise ForbiddenError("This endpoint is for patients.")
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == user.id).one_or_none()
    if profile is None:
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

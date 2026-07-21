"""Department, doctor, and slot schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SlotStatus


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str
    active: bool


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    keywords: str = ""


class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    specialty: str
    department_id: int
    active: bool


class DoctorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    department_id: int
    specialty: str = ""


class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime
    status: SlotStatus


class SlotCreate(BaseModel):
    doctor_id: int
    start_time: datetime
    end_time: datetime

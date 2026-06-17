from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ScopeName = Literal["Scope 1", "Scope 2"]

class EmissionRecordCreate(BaseModel):
    scope: ScopeName
    category: str = Field(..., min_length=2, max_length=100)
    activity_name: str = Field(..., min_length=2, max_length=100)
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=30)
    activity_date: date
    notes: Optional[str] = None


class EmissionFactorInfo(BaseModel):
    id: int
    version_label: str
    factor_source: str
    co2e_kg_per_unit: float
    valid_from: date
    valid_to: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class EmissionRecordResponse(BaseModel):
    id: int
    scope: ScopeName
    category: str
    activity_name: str
    quantity: float
    unit: str
    activity_date: date
    calculated_kg_co2e: float
    final_kg_co2e: float
    override_applied: bool
    notes: Optional[str] = None
    created_at: datetime
    emission_factor: EmissionFactorInfo

    model_config = ConfigDict(from_attributes=True)


class OverrideRequest(BaseModel):
    new_kg_co2e: float = Field(..., ge=0)
    reason: str = Field(..., min_length=5, max_length=500)


class AuditLogResponse(BaseModel):
    id: int
    emission_record_id: int
    action: str
    field_name: str
    old_value: Optional[float] = None
    new_value: Optional[float] = None
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessMetricCreate(BaseModel):
    metric_date: date
    metric_name: str = Field(..., min_length=2, max_length=100)
    metric_unit: str = Field(..., min_length=1, max_length=30)
    value: float = Field(..., ge=0)


class BusinessMetricResponse(BaseModel):
    id: int
    metric_date: date
    metric_name: str
    metric_unit: str
    value: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityOption(BaseModel):
    scope: ScopeName
    category: str
    activity_name: str
    activity_unit: str

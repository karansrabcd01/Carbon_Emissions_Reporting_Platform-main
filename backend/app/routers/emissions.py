from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    ActivityOption,
    AuditLogResponse,
    BusinessMetricCreate,
    BusinessMetricResponse,
    EmissionRecordCreate,
    EmissionRecordResponse,
    OverrideRequest,
)
from .crud import (
    create_business_metric,
    create_emission_record,
    list_activity_options,
    list_audit_logs,
    list_business_metrics,
    list_emission_records,
    override_emission_record,
)


router = APIRouter(tags=["operations"])


@router.get("/emissions", response_model=list[EmissionRecordResponse])
def get_emissions(db: Session = Depends(get_db)):
    return list_emission_records(db)


@router.post("/emissions", response_model=EmissionRecordResponse, status_code=status.HTTP_201_CREATED)
def create_emission(payload: EmissionRecordCreate, db: Session = Depends(get_db)):
    try:
        return create_emission_record(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/emissions/{record_id}/override", response_model=EmissionRecordResponse)
def override_emission(record_id: int, payload: OverrideRequest, db: Session = Depends(get_db)):
    try:
        return override_emission_record(db, record_id, payload)
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/business-metrics", response_model=list[BusinessMetricResponse])
def get_business_metrics(db: Session = Depends(get_db)):
    return list_business_metrics(db)


@router.post("/business-metrics", response_model=BusinessMetricResponse, status_code=status.HTTP_201_CREATED)
def create_metric(payload: BusinessMetricCreate, db: Session = Depends(get_db)):
    return create_business_metric(db, payload)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db)):
    return list_audit_logs(db)


@router.get("/master-data/activity-options", response_model=list[ActivityOption])
def get_activity_options(db: Session = Depends(get_db)):
    options = []
    seen = set()
    for factor in list_activity_options(db):
        key = (factor.scope, factor.category, factor.activity_name, factor.activity_unit)
        if key in seen:
            continue
        seen.add(key)
        options.append(
            ActivityOption(
                scope=factor.scope,
                category=factor.category,
                activity_name=factor.activity_name,
                activity_unit=factor.activity_unit,
            )
        )
    return options

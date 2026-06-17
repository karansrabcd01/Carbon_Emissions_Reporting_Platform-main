from sqlalchemy.orm import Session, joinedload

from ..models import AuditLog, BusinessMetric, EmissionFactor, EmissionRecord
from ..schemas import BusinessMetricCreate, EmissionRecordCreate, OverrideRequest
from ..utils import calculate_emission_kg, get_valid_emission_factor


def create_emission_record(db: Session, payload: EmissionRecordCreate) -> EmissionRecord:
    factor = get_valid_emission_factor(
        db=db,
        scope=payload.scope,
        activity_name=payload.activity_name,
        unit=payload.unit,
        activity_date=payload.activity_date,
    )
    if factor is None:
        raise ValueError(
            f"No valid emission factor found for {payload.activity_name} ({payload.unit}) on {payload.activity_date}."
        )

    calculated_kg_co2e = calculate_emission_kg(payload.quantity, factor.co2e_kg_per_unit)
    record = EmissionRecord(
        scope=payload.scope,
        category=payload.category,
        activity_name=payload.activity_name,
        quantity=payload.quantity,
        unit=payload.unit,
        activity_date=payload.activity_date,
        calculated_kg_co2e=calculated_kg_co2e,
        final_kg_co2e=calculated_kg_co2e,
        notes=payload.notes,
        emission_factor_id=factor.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return (
        db.query(EmissionRecord)
        .options(joinedload(EmissionRecord.emission_factor))
        .filter(EmissionRecord.id == record.id)
        .one()
    )


def list_emission_records(db: Session) -> list[EmissionRecord]:
    return (
        db.query(EmissionRecord)
        .options(joinedload(EmissionRecord.emission_factor))
        .order_by(EmissionRecord.activity_date.desc(), EmissionRecord.id.desc())
        .all()
    )


def override_emission_record(db: Session, record_id: int, payload: OverrideRequest) -> EmissionRecord:
    record = db.query(EmissionRecord).filter(EmissionRecord.id == record_id).first()
    if record is None:
        raise ValueError("Emission record not found.")

    old_value = record.final_kg_co2e
    record.final_kg_co2e = round(payload.new_kg_co2e, 4)
    record.override_applied = True

    db.add(
        AuditLog(
            emission_record_id=record.id,
            action="manual_override",
            field_name="final_kg_co2e",
            old_value=old_value,
            new_value=record.final_kg_co2e,
            reason=payload.reason,
        )
    )
    db.commit()
    db.refresh(record)
    return (
        db.query(EmissionRecord)
        .options(joinedload(EmissionRecord.emission_factor))
        .filter(EmissionRecord.id == record.id)
        .one()
    )


def create_business_metric(db: Session, payload: BusinessMetricCreate) -> BusinessMetric:
    metric = BusinessMetric(
        metric_date=payload.metric_date,
        metric_name=payload.metric_name,
        metric_unit=payload.metric_unit,
        value=payload.value,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def list_business_metrics(db: Session) -> list[BusinessMetric]:
    return db.query(BusinessMetric).order_by(BusinessMetric.metric_date.desc(), BusinessMetric.id.desc()).all()


def list_audit_logs(db: Session) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).all()


def list_activity_options(db: Session) -> list[EmissionFactor]:
    return (
        db.query(EmissionFactor)
        .order_by(
            EmissionFactor.scope.asc(),
            EmissionFactor.activity_name.asc(),
            EmissionFactor.valid_from.desc(),
        )
        .all()
    )

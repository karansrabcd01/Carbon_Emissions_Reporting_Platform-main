from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .models import AuditLog, BusinessMetric, EmissionFactor, EmissionRecord


def get_valid_emission_factor(
    db: Session,
    scope: str,
    activity_name: str,
    unit: str,
    activity_date: date,
) -> EmissionFactor | None:
    return (
        db.query(EmissionFactor)
        .filter(
            EmissionFactor.scope == scope,
            EmissionFactor.activity_name == activity_name,
            EmissionFactor.activity_unit == unit,
            EmissionFactor.valid_from <= activity_date,
            or_(EmissionFactor.valid_to.is_(None), EmissionFactor.valid_to >= activity_date),
        )
        .order_by(EmissionFactor.valid_from.desc(), EmissionFactor.id.desc())
        .first()
    )


def calculate_emission_kg(quantity: float, factor_value: float) -> float:
    return round(quantity * factor_value, 4)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _factor_key_from_values(
    scope: str,
    category: str,
    activity_name: str,
    activity_unit: str,
    co2e_kg_per_unit: float,
    factor_source: str,
    version_label: str,
    valid_from: date,
    valid_to: date | None,
) -> tuple:
    return (
        scope,
        category,
        activity_name,
        activity_unit,
        round(float(co2e_kg_per_unit), 4),
        factor_source,
        version_label,
        valid_from.isoformat(),
        valid_to.isoformat() if valid_to else None,
    )


def _factor_key(factor: EmissionFactor) -> tuple:
    return _factor_key_from_values(
        factor.scope,
        factor.category,
        factor.activity_name,
        factor.activity_unit,
        factor.co2e_kg_per_unit,
        factor.factor_source,
        factor.version_label,
        factor.valid_from,
        factor.valid_to,
    )


def _metric_key(metric_date: date, metric_name: str, metric_unit: str, value: float) -> tuple:
    return (metric_date.isoformat(), metric_name, metric_unit, round(float(value), 4))


def _record_key(
    scope: str,
    category: str,
    activity_name: str,
    quantity: float,
    unit: str,
    activity_date: date,
    calculated_kg_co2e: float,
    final_kg_co2e: float,
    notes: str | None,
    override_applied: bool,
    factor_key: tuple | None,
) -> tuple:
    return (
        scope,
        category,
        activity_name,
        round(float(quantity), 4),
        unit,
        activity_date.isoformat(),
        round(float(calculated_kg_co2e), 4),
        round(float(final_kg_co2e), 4),
        (notes or "").strip(),
        bool(override_applied),
        factor_key,
    )


def migrate_legacy_sqlite_data(db: Session, source_path: Path | None, target_path: Path | None) -> None:
    if source_path is None or target_path is None:
        return

    source_path = Path(source_path).resolve()
    target_path = Path(target_path).resolve()
    if not source_path.exists() or source_path == target_path:
        return

    with sqlite3.connect(source_path) as connection:
        connection.row_factory = sqlite3.Row
        factor_rows = connection.execute("SELECT * FROM emission_factors").fetchall()
        metric_rows = connection.execute("SELECT * FROM business_metrics ORDER BY id ASC").fetchall()
        record_rows = connection.execute("SELECT * FROM emission_records ORDER BY id ASC").fetchall()
        audit_rows = connection.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()

    factor_ids_by_key = {_factor_key(factor): factor.id for factor in db.query(EmissionFactor).all()}

    legacy_factor_keys: dict[int, tuple | None] = {}
    for row in factor_rows:
        valid_from = _parse_date(row["valid_from"])
        if valid_from is None:
            continue

        legacy_factor_keys[row["id"]] = _factor_key_from_values(
            row["scope"],
            row["category"],
            row["activity_name"],
            row["activity_unit"],
            row["co2e_kg_per_unit"],
            row["factor_source"],
            row["version_label"],
            valid_from,
            _parse_date(row["valid_to"]),
        )

    existing_metric_keys = {
        _metric_key(metric.metric_date, metric.metric_name, metric.metric_unit, metric.value): metric.id
        for metric in db.query(BusinessMetric).all()
    }
    for row in metric_rows:
        metric_date = _parse_date(row["metric_date"])
        if metric_date is None:
            continue

        key = _metric_key(metric_date, row["metric_name"], row["metric_unit"], row["value"])
        if key in existing_metric_keys:
            continue

        metric = BusinessMetric(
            metric_date=metric_date,
            metric_name=row["metric_name"],
            metric_unit=row["metric_unit"],
            value=row["value"],
            created_at=_parse_datetime(row["created_at"]) or datetime.utcnow(),
        )
        db.add(metric)
        db.flush()
        existing_metric_keys[key] = metric.id

    existing_record_keys = {}
    for record in db.query(EmissionRecord).join(EmissionRecord.emission_factor).all():
        factor_key = _factor_key(record.emission_factor) if record.emission_factor else None
        key = _record_key(
            record.scope,
            record.category,
            record.activity_name,
            record.quantity,
            record.unit,
            record.activity_date,
            record.calculated_kg_co2e,
            record.final_kg_co2e,
            record.notes,
            record.override_applied,
            factor_key,
        )
        existing_record_keys[key] = record.id

    legacy_to_current_record_ids: dict[int, int] = {}
    for row in record_rows:
        activity_date = _parse_date(row["activity_date"])
        if activity_date is None:
            continue

        factor_key = legacy_factor_keys.get(row["emission_factor_id"])
        current_factor_id = factor_ids_by_key.get(factor_key) if factor_key else None
        if current_factor_id is None:
            continue

        key = _record_key(
            row["scope"],
            row["category"],
            row["activity_name"],
            row["quantity"],
            row["unit"],
            activity_date,
            row["calculated_kg_co2e"],
            row["final_kg_co2e"],
            row["notes"],
            row["override_applied"],
            factor_key,
        )
        if key in existing_record_keys:
            legacy_to_current_record_ids[row["id"]] = existing_record_keys[key]
            continue

        record = EmissionRecord(
            scope=row["scope"],
            category=row["category"],
            activity_name=row["activity_name"],
            quantity=row["quantity"],
            unit=row["unit"],
            activity_date=activity_date,
            calculated_kg_co2e=row["calculated_kg_co2e"],
            final_kg_co2e=row["final_kg_co2e"],
            notes=row["notes"],
            override_applied=bool(row["override_applied"]),
            created_at=_parse_datetime(row["created_at"]) or datetime.utcnow(),
            emission_factor_id=current_factor_id,
        )
        db.add(record)
        db.flush()
        existing_record_keys[key] = record.id
        legacy_to_current_record_ids[row["id"]] = record.id

    existing_audit_keys = {
        (
            audit.emission_record_id,
            audit.action,
            audit.field_name,
            audit.old_value,
            audit.new_value,
            audit.reason,
            audit.created_at.isoformat(),
        )
        for audit in db.query(AuditLog).all()
    }
    for row in audit_rows:
        current_record_id = legacy_to_current_record_ids.get(row["emission_record_id"])
        if current_record_id is None:
            continue

        created_at = _parse_datetime(row["created_at"]) or datetime.utcnow()
        key = (
            current_record_id,
            row["action"],
            row["field_name"],
            row["old_value"],
            row["new_value"],
            row["reason"],
            created_at.isoformat(),
        )
        if key in existing_audit_keys:
            continue

        db.add(
            AuditLog(
                emission_record_id=current_record_id,
                action=row["action"],
                field_name=row["field_name"],
                old_value=row["old_value"],
                new_value=row["new_value"],
                reason=row["reason"],
                created_at=created_at,
            )
        )
        existing_audit_keys.add(key)

    db.commit()


def seed_sample_data(db: Session) -> None:
    if db.query(EmissionFactor).count() == 0:
        db.add_all(
            [
                EmissionFactor(
                    scope="Scope 1",
                    category="Mobile Combustion",
                    activity_name="Diesel",
                    activity_unit="liters",
                    co2e_kg_per_unit=2.6800,
                    factor_source="Sample DEFRA aligned dataset",
                    version_label="2024-v1",
                    valid_from=date(2024, 1, 1),
                    valid_to=date(2024, 12, 31),
                ),
                EmissionFactor(
                    scope="Scope 1",
                    category="Mobile Combustion",
                    activity_name="Diesel",
                    activity_unit="liters",
                    co2e_kg_per_unit=2.6600,
                    factor_source="Sample DEFRA aligned dataset",
                    version_label="2025-v1",
                    valid_from=date(2025, 1, 1),
                    valid_to=date(2025, 12, 31),
                ),
                EmissionFactor(
                    scope="Scope 1",
                    category="Mobile Combustion",
                    activity_name="Diesel",
                    activity_unit="liters",
                    co2e_kg_per_unit=2.6400,
                    factor_source="Sample DEFRA aligned dataset",
                    version_label="2026-v1",
                    valid_from=date(2026, 1, 1),
                    valid_to=None,
                ),
                EmissionFactor(
                    scope="Scope 1",
                    category="Stationary Combustion",
                    activity_name="LPG",
                    activity_unit="kg",
                    co2e_kg_per_unit=3.0100,
                    factor_source="Sample EPA stationary fuel factor",
                    version_label="2024-v1",
                    valid_from=date(2024, 1, 1),
                    valid_to=date(2024, 12, 31),
                ),
                EmissionFactor(
                    scope="Scope 1",
                    category="Stationary Combustion",
                    activity_name="LPG",
                    activity_unit="kg",
                    co2e_kg_per_unit=2.9800,
                    factor_source="Sample EPA stationary fuel factor",
                    version_label="2025-v1",
                    valid_from=date(2025, 1, 1),
                    valid_to=date(2025, 12, 31),
                ),
                EmissionFactor(
                    scope="Scope 1",
                    category="Stationary Combustion",
                    activity_name="LPG",
                    activity_unit="kg",
                    co2e_kg_per_unit=2.9500,
                    factor_source="Sample EPA stationary fuel factor",
                    version_label="2026-v1",
                    valid_from=date(2026, 1, 1),
                    valid_to=None,
                ),
                EmissionFactor(
                    scope="Scope 2",
                    category="Purchased Electricity",
                    activity_name="Grid Electricity",
                    activity_unit="kWh",
                    co2e_kg_per_unit=0.8200,
                    factor_source="Sample grid electricity factor",
                    version_label="2024-v1",
                    valid_from=date(2024, 1, 1),
                    valid_to=date(2024, 12, 31),
                ),
                EmissionFactor(
                    scope="Scope 2",
                    category="Purchased Electricity",
                    activity_name="Grid Electricity",
                    activity_unit="kWh",
                    co2e_kg_per_unit=0.7900,
                    factor_source="Sample grid electricity factor",
                    version_label="2025-v1",
                    valid_from=date(2025, 1, 1),
                    valid_to=date(2025, 12, 31),
                ),
                EmissionFactor(
                    scope="Scope 2",
                    category="Purchased Electricity",
                    activity_name="Grid Electricity",
                    activity_unit="kWh",
                    co2e_kg_per_unit=0.7500,
                    factor_source="Sample grid electricity factor",
                    version_label="2026-v1",
                    valid_from=date(2026, 1, 1),
                    valid_to=None,
                ),
            ]
        )
        db.commit()

    if db.query(BusinessMetric).count() == 0:
        db.add_all(
            [
                BusinessMetric(metric_date=date(2025, 1, 31), metric_name="Tons of Steel Produced", metric_unit="tons", value=4800),
                BusinessMetric(metric_date=date(2025, 2, 28), metric_name="Tons of Steel Produced", metric_unit="tons", value=4950),
                BusinessMetric(metric_date=date(2025, 3, 31), metric_name="Tons of Steel Produced", metric_unit="tons", value=5100),
                BusinessMetric(metric_date=date(2025, 4, 30), metric_name="Tons of Steel Produced", metric_unit="tons", value=5200),
                BusinessMetric(metric_date=date(2026, 1, 31), metric_name="Tons of Steel Produced", metric_unit="tons", value=5300),
                BusinessMetric(metric_date=date(2026, 2, 28), metric_name="Tons of Steel Produced", metric_unit="tons", value=5450),
                BusinessMetric(metric_date=date(2026, 3, 31), metric_name="Tons of Steel Produced", metric_unit="tons", value=5600),
                BusinessMetric(metric_date=date(2026, 4, 30), metric_name="Tons of Steel Produced", metric_unit="tons", value=5700),
                BusinessMetric(metric_date=date(2025, 12, 31), metric_name="Employees", metric_unit="employees", value=1120),
                BusinessMetric(metric_date=date(2026, 3, 31), metric_name="Employees", metric_unit="employees", value=1155),
            ]
        )
        db.commit()

    if db.query(EmissionRecord).count() == 0:
        sample_records = [
            ("Scope 1", "Mobile Combustion", "Diesel", 12000, "liters", date(2025, 1, 15), "Fleet fuel consumption"),
            ("Scope 1", "Stationary Combustion", "LPG", 1800, "kg", date(2025, 2, 10), "Boiler usage"),
            ("Scope 2", "Purchased Electricity", "Grid Electricity", 85000, "kWh", date(2025, 3, 20), "Plant electricity"),
            ("Scope 1", "Mobile Combustion", "Diesel", 13400, "liters", date(2025, 4, 18), "Logistics operations"),
            ("Scope 2", "Purchased Electricity", "Grid Electricity", 91000, "kWh", date(2025, 5, 20), "Plant electricity"),
            ("Scope 1", "Stationary Combustion", "LPG", 1650, "kg", date(2025, 6, 8), "Heat treatment"),
            ("Scope 1", "Mobile Combustion", "Diesel", 12500, "liters", date(2026, 1, 16), "Fleet fuel consumption"),
            ("Scope 2", "Purchased Electricity", "Grid Electricity", 88000, "kWh", date(2026, 1, 25), "Plant electricity"),
            ("Scope 1", "Stationary Combustion", "LPG", 1900, "kg", date(2026, 2, 11), "Boiler usage"),
            ("Scope 2", "Purchased Electricity", "Grid Electricity", 94000, "kWh", date(2026, 2, 23), "Plant electricity"),
            ("Scope 1", "Mobile Combustion", "Diesel", 14200, "liters", date(2026, 3, 14), "Outbound transport"),
            ("Scope 2", "Purchased Electricity", "Grid Electricity", 97000, "kWh", date(2026, 3, 27), "Plant electricity"),
            ("Scope 1", "Mobile Combustion", "Diesel", 13800, "liters", date(2026, 4, 9), "Inbound logistics"),
            ("Scope 2", "Purchased Electricity", "Grid Electricity", 99000, "kWh", date(2026, 4, 21), "Plant electricity"),
        ]

        for scope, category, activity_name, quantity, unit, activity_date, notes in sample_records:
            factor = get_valid_emission_factor(db, scope, activity_name, unit, activity_date)
            if factor is None:
                continue

            emissions = calculate_emission_kg(quantity, factor.co2e_kg_per_unit)
            db.add(
                EmissionRecord(
                    scope=scope,
                    category=category,
                    activity_name=activity_name,
                    quantity=quantity,
                    unit=unit,
                    activity_date=activity_date,
                    calculated_kg_co2e=emissions,
                    final_kg_co2e=emissions,
                    notes=notes,
                    emission_factor_id=factor.id,
                )
            )

        db.commit()

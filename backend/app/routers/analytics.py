from calendar import month_abbr
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BusinessMetric, EmissionRecord


router = APIRouter(prefix="/analytics", tags=["analytics"])


def _date_filters(start_date: date | None, end_date: date | None):
    filters = []
    if start_date is not None:
        filters.append(EmissionRecord.activity_date >= start_date)
    if end_date is not None:
        filters.append(EmissionRecord.activity_date <= end_date)
    return filters


def _metric_filters(start_date: date | None, end_date: date | None):
    filters = []
    if start_date is not None:
        filters.append(BusinessMetric.metric_date >= start_date)
    if end_date is not None:
        filters.append(BusinessMetric.metric_date <= end_date)
    return filters


@router.get("/yoy-emissions")
def get_yoy_emissions(
    year: int = Query(default=date.today().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
):
    previous_year = year - 1

    results = (
        db.query(
            extract("year", EmissionRecord.activity_date).label("year"),
            EmissionRecord.scope.label("scope"),
            func.sum(EmissionRecord.final_kg_co2e).label("total_kg_co2e"),
        )
        .filter(extract("year", EmissionRecord.activity_date).in_([previous_year, year]))
        .group_by("year", "scope")
        .all()
    )

    payload = {
        previous_year: {"Scope 1": 0.0, "Scope 2": 0.0},
        year: {"Scope 1": 0.0, "Scope 2": 0.0},
    }
    for row in results:
        payload[int(row.year)][row.scope] = round(row.total_kg_co2e or 0.0, 2)

    return {
        "year": year,
        "previous_year": previous_year,
        "unit": "kgCO2e",
        "series": [
            {"year": previous_year, "scope_1": payload[previous_year]["Scope 1"], "scope_2": payload[previous_year]["Scope 2"]},
            {"year": year, "scope_1": payload[year]["Scope 1"], "scope_2": payload[year]["Scope 2"]},
        ],
    }


@router.get("/emission-intensity")
def get_emission_intensity(
    metric_name: str = Query(default="Tons of Steel Produced"),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    total_emissions = (
        db.query(func.sum(EmissionRecord.final_kg_co2e))
        .filter(*_date_filters(start_date, end_date))
        .scalar()
        or 0.0
    )

    metric_query = db.query(
        func.sum(BusinessMetric.value).label("metric_total"),
        func.max(BusinessMetric.metric_unit).label("metric_unit"),
    ).filter(BusinessMetric.metric_name == metric_name, *_metric_filters(start_date, end_date))
    metric_total, metric_unit = metric_query.one()

    if not metric_total:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No business metric data found for '{metric_name}' in the requested period.",
        )

    return {
        "metric_name": metric_name,
        "metric_unit": metric_unit,
        "emissions_kg_co2e": round(total_emissions, 2),
        "business_metric_total": round(metric_total, 2),
        "intensity_kg_co2e_per_unit": round(total_emissions / metric_total, 4),
        "start_date": start_date,
        "end_date": end_date,
    }


@router.get("/hotspots")
def get_hotspots(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            EmissionRecord.activity_name,
            EmissionRecord.scope,
            func.sum(EmissionRecord.final_kg_co2e).label("total_kg_co2e"),
        )
        .filter(*_date_filters(start_date, end_date))
        .group_by(EmissionRecord.activity_name, EmissionRecord.scope)
        .order_by(func.sum(EmissionRecord.final_kg_co2e).desc())
        .all()
    )

    total = sum((row.total_kg_co2e or 0.0) for row in rows) or 1.0
    return {
        "unit": "kgCO2e",
        "items": [
            {
                "activity_name": row.activity_name,
                "scope": row.scope,
                "total_kg_co2e": round(row.total_kg_co2e or 0.0, 2),
                "share_percent": round(((row.total_kg_co2e or 0.0) / total) * 100, 2),
            }
            for row in rows
        ],
    }


@router.get("/monthly-emissions")
def get_monthly_emissions(
    year: int = Query(default=date.today().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            extract("month", EmissionRecord.activity_date).label("month"),
            func.sum(EmissionRecord.final_kg_co2e).label("total_kg_co2e"),
        )
        .filter(extract("year", EmissionRecord.activity_date) == year)
        .group_by("month")
        .order_by("month")
        .all()
    )

    monthly_totals = {int(row.month): round(row.total_kg_co2e or 0.0, 2) for row in rows}
    return {
        "year": year,
        "unit": "kgCO2e",
        "series": [
            {
                "month": month_index,
                "label": month_abbr[month_index],
                "total_kg_co2e": monthly_totals.get(month_index, 0.0),
            }
            for month_index in range(1, 13)
        ],
    }

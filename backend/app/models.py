from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    activity_name = Column(String, nullable=False, index=True)
    activity_unit = Column(String, nullable=False)
    co2e_kg_per_unit = Column(Float, nullable=False)
    factor_source = Column(String, nullable=False)
    version_label = Column(String, nullable=False)
    valid_from = Column(Date, nullable=False, index=True)
    valid_to = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    records = relationship("EmissionRecord", back_populates="emission_factor")


class EmissionRecord(Base):
    __tablename__ = "emission_records"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    activity_name = Column(String, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    activity_date = Column(Date, nullable=False, index=True)
    calculated_kg_co2e = Column(Float, nullable=False)
    final_kg_co2e = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    override_applied = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    emission_factor_id = Column(Integer, ForeignKey("emission_factors.id"), nullable=False)

    emission_factor = relationship("EmissionFactor", back_populates="records")
    audit_logs = relationship("AuditLog", back_populates="record", cascade="all, delete-orphan")


class BusinessMetric(Base):
    __tablename__ = "business_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_date = Column(Date, nullable=False, index=True)
    metric_name = Column(String, nullable=False, index=True)
    metric_unit = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    emission_record_id = Column(Integer, ForeignKey("emission_records.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    field_name = Column(String, nullable=False)
    old_value = Column(Float, nullable=True)
    new_value = Column(Float, nullable=True)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    record = relationship("EmissionRecord", back_populates="audit_logs")

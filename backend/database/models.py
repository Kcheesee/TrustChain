"""
SQLAlchemy ORM Models for TrustChain.

Maps Python objects to PostgreSQL tables for clean database access.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, TIMESTAMP,
    ForeignKey, ARRAY, JSON, CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Dict, Any

Base = declarative_base()


class Decision(Base):
    """Main decision record with audit trail."""
    __tablename__ = "decisions"
    
    decision_id = Column(String(255), primary_key=True)
    case_id = Column(String(255), nullable=False, index=True)
    case_type = Column(String(100), nullable=False)
    decision_type = Column(String(100), nullable=False, index=True)
    
    # Final decision
    final_decision = Column(String(50))
    status = Column(String(50), nullable=False, default="pending", index=True)
    
    # Consensus metrics
    consensus_level = Column(Float)
    avg_confidence = Column(Float)
    confidence_variance = Column(Float)
    
    # Audit
    audit_hash = Column(String(64), nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    completed_at = Column(TIMESTAMP)
    reviewed_at = Column(TIMESTAMP)
    
    # Relationships
    model_decisions = relationship("ModelDecision", back_populates="decision", cascade="all, delete-orphan")
    bias_analysis = relationship("BiasAnalysis", back_populates="decision", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="decision", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint('consensus_level >= 0 AND consensus_level <= 1', name='valid_consensus'),
        CheckConstraint('avg_confidence >= 0 AND avg_confidence <= 1', name='valid_confidence'),
    )
    
    def __repr__(self):
        return f"<Decision(id={self.decision_id}, case={self.case_id}, status={self.status})>"


class ModelDecision(Base):
    """Individual AI model response."""
    __tablename__ = "model_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(String(255), ForeignKey("decisions.decision_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Model info
    provider = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50))
    
    # Decision
    decision = Column(String(50), nullable=False)
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Performance metrics
    latency_ms = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    estimated_cost = Column(Float)
    
    # Timestamp
    timestamp = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    
    # Relationships
    decision = relationship("Decision", back_populates="model_decisions")
    
    __table_args__ = (
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='valid_model_confidence'),
    )
    
    def __repr__(self):
        return f"<ModelDecision(provider={self.provider}, decision={self.decision}, confidence={self.confidence:.2f})>"


class BiasAnalysis(Base):
    """Bias detection results."""
    __tablename__ = "bias_analyses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(String(255), ForeignKey("decisions.decision_id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    
    # Bias detection
    bias_detected = Column(Boolean, nullable=False, default=False, index=True)
    bias_score = Column(Float)
    
    # Protected attributes
    protected_attributes_found = Column(ARRAY(Text))
    
    # Safety
    safety_triggers = Column(ARRAY(Text))
    requires_human_review = Column(Boolean, nullable=False, default=False, index=True)
    
    # Analysis
    bias_type = Column(String(100))
    affected_attributes = Column(JSON)
    recommendation = Column(Text)
    
    # Timestamp
    analyzed_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    
    # Relationships
    decision = relationship("Decision", back_populates="bias_analysis")
    
    def __repr__(self):
        return f"<BiasAnalysis(decision_id={self.decision_id}, bias_detected={self.bias_detected})>"


class AuditLog(Base):
    """Immutable audit trail."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(String(255), ForeignKey("decisions.decision_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Event info
    event_type = Column(String(100), nullable=False, index=True)
    event_details = Column(JSON, nullable=False)
    
    # Actor
    actor = Column(String(255), index=True)
    actor_type = Column(String(50))
    
    # Request info
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    
    # Timestamp (immutable)
    timestamp = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    
    # Cryptographic proof
    event_hash = Column(String(64), nullable=False)
    
    # Relationships
    decision = relationship("Decision", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(event_type={self.event_type}, timestamp={self.timestamp})>"


class ProviderHealth(Base):
    """AI provider health monitoring."""
    __tablename__ = "provider_health"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    
    # Health metrics
    status = Column(String(50), nullable=False)  # healthy, degraded, down
    success_rate = Column(Float)
    avg_latency_ms = Column(Integer)
    error_count = Column(Integer, default=0)
    
    # Timestamp
    checked_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    
    __table_args__ = (
        CheckConstraint('success_rate >= 0 AND success_rate <= 1', name='valid_success_rate'),
    )
    
    def __repr__(self):
        return f"<ProviderHealth(provider={self.provider}, status={self.status})>"


# Additional models for future features

class User(Base):
    """System users for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255))
    department = Column(String(100))
    role = Column(String(50), nullable=False, default="reviewer", index=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    last_login_at = Column(TIMESTAMP)
    
    def __repr__(self):
        return f"<User(username={self.username}, role={self.role})>"

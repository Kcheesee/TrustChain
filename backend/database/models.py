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


# ============================================================================
# Phase 3: Feedback & Learning Models
# ============================================================================

class HumanFeedback(Base):
    """Human reviewer feedback on AI decisions."""
    __tablename__ = "human_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feedback_id = Column(String(255), unique=True, nullable=False, index=True)
    result_id = Column(String(255), nullable=False, index=True)  # Links to TrustChain result

    # Reviewer info
    reviewer_id = Column(String(255), nullable=False, index=True)

    # Action taken
    action = Column(String(50), nullable=False, index=True)  # AGREE, OVERRIDE_TO_APPROVE, OVERRIDE_TO_DENY, ESCALATE
    original_decision = Column(String(50), nullable=False)
    final_decision = Column(String(50), nullable=False)

    # Override details (nullable if action is AGREE)
    override_reason = Column(String(100))
    confidence_adjustment = Column(Float)

    # Context
    decision_type = Column(String(100), index=True)
    notes = Column(Text)

    # Outcome tracking (filled in later when real-world outcome known)
    outcome = Column(String(50))  # CORRECT, INCORRECT, UNKNOWN
    outcome_recorded_at = Column(TIMESTAMP)

    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)

    __table_args__ = (
        CheckConstraint(
            "action IN ('AGREE', 'OVERRIDE_TO_APPROVE', 'OVERRIDE_TO_DENY', 'ESCALATE')",
            name='valid_action'
        ),
    )

    def __repr__(self):
        return f"<HumanFeedback(id={self.feedback_id}, action={self.action}, reviewer={self.reviewer_id})>"


class ReviewerCredibility(Base):
    """Tracks reviewer credibility based on outcomes."""
    __tablename__ = "reviewer_credibility"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reviewer_id = Column(String(255), unique=True, nullable=False, index=True)

    # Review counts
    total_reviews = Column(Integer, nullable=False, default=0)
    total_overrides = Column(Integer, nullable=False, default=0)

    # Outcome tracking
    outcomes_recorded = Column(Integer, nullable=False, default=0)
    correct_decisions = Column(Integer, nullable=False, default=0)

    # Credibility score (0.0 - 1.0, based on outcomes)
    credibility_score = Column(Float, nullable=False, default=0.5)

    # Anomaly tracking
    flagged = Column(Boolean, nullable=False, default=False, index=True)
    flag_reason = Column(String(255))
    flagged_at = Column(TIMESTAMP)

    # Timestamps
    first_review_at = Column(TIMESTAMP, server_default=func.now())
    last_review_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint('credibility_score >= 0 AND credibility_score <= 1', name='valid_credibility'),
    )

    def __repr__(self):
        return f"<ReviewerCredibility(reviewer={self.reviewer_id}, score={self.credibility_score:.2f}, flagged={self.flagged})>"


class ParameterVersion(Base):
    """Versioned learning parameters for rollback capability."""
    __tablename__ = "parameter_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, nullable=False, unique=True, index=True)

    # Parameters (stored as JSON)
    model_weights = Column(JSON)
    confidence_adjustments = Column(JSON)
    analyzer_sensitivity = Column(JSON)

    # Metadata
    feedback_count = Column(Integer, nullable=False, default=0)
    notes = Column(Text)

    # Corruption detection
    checksum = Column(String(64))

    # Timestamps
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)

    def __repr__(self):
        return f"<ParameterVersion(version={self.version}, feedback_count={self.feedback_count})>"


class LearningRun(Base):
    """Audit trail for learning cycles."""
    __tablename__ = "learning_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(255), unique=True, nullable=False, index=True)

    # Run details
    feedback_processed = Column(Integer, nullable=False, default=0)
    reviewers_included = Column(Integer, nullable=False, default=0)
    reviewers_excluded = Column(Integer, nullable=False, default=0)

    # Results
    parameter_version_before = Column(Integer)
    parameter_version_after = Column(Integer)

    # Status
    status = Column(String(50), nullable=False, default="running", index=True)  # running, completed, failed, rolled_back
    error_message = Column(Text)

    # Timestamps
    started_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP)

    def __repr__(self):
        return f"<LearningRun(id={self.run_id}, status={self.status}, feedback={self.feedback_processed})>"

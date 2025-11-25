"""
Repository Pattern for TrustChain Database Access.

Provides clean interface for CRUD operations, hiding SQLAlchemy complexity.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from database.models import (
    Decision, ModelDecision, BiasAnalysis, AuditLog, ProviderHealth,
    HumanFeedback, ReviewerCredibility, ParameterVersion, LearningRun
)

logger = logging.getLogger(__name__)


class DecisionRepository:
    """Repository for decision CRUD operations."""
    
    def __init__(self, session: Session):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def create(self, decision_data: Dict[str, Any]) -> Decision:
        """
        Create a new decision record.
        
        Args:
            decision_data: Decision attributes
            
        Returns:
            Created Decision object
        """
        decision = Decision(**decision_data)
        self.session.add(decision)
        self.session.commit()
        self.session.refresh(decision)
        
        logger.info(f"Created decision: {decision.decision_id}")
        return decision
    
    def get_by_id(self, decision_id: str) -> Optional[Decision]:
        """
        Get decision by ID.
        
        Args:
            decision_id: Decision identifier
            
        Returns:
            Decision object or None
        """
        return self.session.query(Decision).filter(
            Decision.decision_id == decision_id
        ).first()
    
    def get_by_case_id(self, case_id: str) -> List[Decision]:
        """
        Get all decisions for a case.
        
        Args:
            case_id: Case identifier
            
        Returns:
            List of Decision objects
        """
        return self.session.query(Decision).filter(
            Decision.case_id == case_id
        ).order_by(desc(Decision.created_at)).all()
    
    def list_recent(self, limit: int = 100, status: Optional[str] = None) -> List[Decision]:
        """
        List recent decisions.
        
        Args:
            limit: Maximum number of results
            status: Optional status filter
            
        Returns:
            List of Decision objects
        """
        query = self.session.query(Decision)
        
        if status:
            query = query.filter(Decision.status == status)
        
        return query.order_by(desc(Decision.created_at)).limit(limit).all()
    
    def update(self, decision_id: str, updates: Dict[str, Any]) -> Optional[Decision]:
        """
        Update decision record.
        
        Args:
            decision_id: Decision identifier
            updates: Fields to update
            
        Returns:
            Updated Decision object or None
        """
        decision = self.get_by_id(decision_id)
        if not decision:
            return None
        
        for key, value in updates.items():
            setattr(decision, key, value)
        
        self.session.commit()
        self.session.refresh(decision)
        
        logger.info(f"Updated decision: {decision_id}")
        return decision
    
    def get_requiring_review(self) -> List[Decision]:
        """
        Get decisions requiring human review.
        
        Returns:
            List of Decision objects
        """
        return self.session.query(Decision).join(BiasAnalysis).filter(
            and_(
                BiasAnalysis.requires_human_review == True,
                Decision.status == 'pending'
            )
        ).order_by(desc(Decision.created_at)).all()


class ModelDecisionRepository:
    """Repository for model decision operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, model_decision_data: Dict[str, Any]) -> ModelDecision:
        """Create model decision record."""
        model_decision = ModelDecision(**model_decision_data)
        self.session.add(model_decision)
        self.session.commit()
        self.session.refresh(model_decision)
        
        logger.info(f"Created model decision for {model_decision.decision_id}")
        return model_decision
    
    def create_bulk(self, model_decisions_data: List[Dict[str, Any]]) -> List[ModelDecision]:
        """
        Create multiple model decisions at once.
        
        Args:
            model_decisions_data: List of model decision attributes
            
        Returns:
            List of created ModelDecision objects
        """
        model_decisions = [ModelDecision(**data) for data in model_decisions_data]
        self.session.add_all(model_decisions)
        self.session.commit()
        
        for md in model_decisions:
            self.session.refresh(md)
        
        logger.info(f"Created {len(model_decisions)} model decisions")
        return model_decisions
    
    def get_by_decision_id(self, decision_id: str) -> List[ModelDecision]:
        """Get all model decisions for a decision."""
        return self.session.query(ModelDecision).filter(
            ModelDecision.decision_id == decision_id
        ).all()


class BiasAnalysisRepository:
    """Repository for bias analysis operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, bias_data: Dict[str, Any]) -> BiasAnalysis:
        """Create bias analysis record."""
        bias_analysis = BiasAnalysis(**bias_data)
        self.session.add(bias_analysis)
        self.session.commit()
        self.session.refresh(bias_analysis)
        
        logger.info(f"Created bias analysis for {bias_analysis.decision_id}")
        return bias_analysis
    
    def get_by_decision_id(self, decision_id: str) -> Optional[BiasAnalysis]:
        """Get bias analysis for a decision."""
        return self.session.query(BiasAnalysis).filter(
            BiasAnalysis.decision_id == decision_id
        ).first()
    
    def get_flagged_decisions(self, limit: int = 100) -> List[BiasAnalysis]:
        """
        Get decisions with bias detected.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of BiasAnalysis objects
        """
        return self.session.query(BiasAnalysis).filter(
            BiasAnalysis.bias_detected == True
        ).order_by(desc(BiasAnalysis.analyzed_at)).limit(limit).all()


class AuditLogRepository:
    """Repository for audit log operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, audit_data: Dict[str, Any]) -> AuditLog:
        """
        Create audit log entry.
        
        Note: Audit logs are immutable - no update/delete methods.
        
        Args:
            audit_data: Audit log attributes
            
        Returns:
            Created AuditLog object
        """
        audit_log = AuditLog(**audit_data)
        self.session.add(audit_log)
        self.session.commit()
        self.session.refresh(audit_log)
        
        logger.debug(f"Created audit log: {audit_log.event_type}")
        return audit_log
    
    def get_by_decision_id(self, decision_id: str) -> List[AuditLog]:
        """Get all audit logs for a decision."""
        return self.session.query(AuditLog).filter(
            AuditLog.decision_id == decision_id
        ).order_by(AuditLog.timestamp).all()
    
    def get_recent(self, limit: int = 1000) -> List[AuditLog]:
        """Get recent audit logs."""
        return self.session.query(AuditLog).order_by(
            desc(AuditLog.timestamp)
        ).limit(limit).all()


class ProviderHealthRepository:
    """Repository for provider health monitoring."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, health_data: Dict[str, Any]) -> ProviderHealth:
        """Create provider health record."""
        health = ProviderHealth(**health_data)
        self.session.add(health)
        self.session.commit()
        self.session.refresh(health)
        
        logger.debug(f"Recorded health for {health.provider}")
        return health
    
    def get_latest_by_provider(self, provider: str) -> Optional[ProviderHealth]:
        """Get latest health check for a provider."""
        return self.session.query(ProviderHealth).filter(
            ProviderHealth.provider == provider
        ).order_by(desc(ProviderHealth.checked_at)).first()
    
    def get_all_latest(self) -> List[ProviderHealth]:
        """Get latest health for all providers."""
        # This is a simplified version - in production you'd use a window function
        providers = self.session.query(ProviderHealth.provider).distinct().all()
        
        latest_health = []
        for (provider,) in providers:
            health = self.get_latest_by_provider(provider)
            if health:
                latest_health.append(health)
        
        return latest_health


# ============================================================================
# Phase 3: Feedback & Learning Repositories
# ============================================================================

class HumanFeedbackRepository:
    """Repository for human feedback operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, feedback_data: Dict[str, Any]) -> HumanFeedback:
        """Create human feedback record."""
        feedback = HumanFeedback(**feedback_data)
        self.session.add(feedback)
        self.session.commit()
        self.session.refresh(feedback)

        logger.info(f"Created feedback: {feedback.feedback_id}")
        return feedback

    def get_by_id(self, feedback_id: str) -> Optional[HumanFeedback]:
        """Get feedback by ID."""
        return self.session.query(HumanFeedback).filter(
            HumanFeedback.feedback_id == feedback_id
        ).first()

    def get_by_result_id(self, result_id: str) -> Optional[HumanFeedback]:
        """Get feedback for a TrustChain result."""
        return self.session.query(HumanFeedback).filter(
            HumanFeedback.result_id == result_id
        ).first()

    def list_by_reviewer(
        self,
        reviewer_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[HumanFeedback]:
        """List feedback by reviewer."""
        return self.session.query(HumanFeedback).filter(
            HumanFeedback.reviewer_id == reviewer_id
        ).order_by(desc(HumanFeedback.created_at)).limit(limit).offset(offset).all()

    def list_overrides(self, limit: int = 100) -> List[HumanFeedback]:
        """List feedback with overrides."""
        override_actions = ['OVERRIDE_TO_APPROVE', 'OVERRIDE_TO_DENY']
        return self.session.query(HumanFeedback).filter(
            HumanFeedback.action.in_(override_actions)
        ).order_by(desc(HumanFeedback.created_at)).limit(limit).all()

    def update_outcome(
        self,
        result_id: str,
        outcome: str,
        notes: str = ""
    ) -> Optional[HumanFeedback]:
        """Update feedback with outcome."""
        feedback = self.get_by_result_id(result_id)
        if feedback:
            feedback.outcome = outcome
            feedback.outcome_recorded_at = datetime.now()
            if notes:
                feedback.notes = (feedback.notes or "") + f"\n\nOutcome: {notes}"
            self.session.commit()
            self.session.refresh(feedback)
        return feedback

    def count_by_reviewer(self, reviewer_id: str) -> Dict[str, int]:
        """Count feedback stats for a reviewer."""
        total = self.session.query(HumanFeedback).filter(
            HumanFeedback.reviewer_id == reviewer_id
        ).count()

        overrides = self.session.query(HumanFeedback).filter(
            HumanFeedback.reviewer_id == reviewer_id,
            HumanFeedback.action.in_(['OVERRIDE_TO_APPROVE', 'OVERRIDE_TO_DENY'])
        ).count()

        return {"total": total, "overrides": overrides}


class ReviewerCredibilityRepository:
    """Repository for reviewer credibility tracking."""

    def __init__(self, session: Session):
        self.session = session

    def get_or_create(self, reviewer_id: str) -> ReviewerCredibility:
        """Get or create reviewer credibility record."""
        cred = self.session.query(ReviewerCredibility).filter(
            ReviewerCredibility.reviewer_id == reviewer_id
        ).first()

        if not cred:
            cred = ReviewerCredibility(reviewer_id=reviewer_id)
            self.session.add(cred)
            self.session.commit()
            self.session.refresh(cred)
            logger.info(f"Created credibility record for reviewer: {reviewer_id}")

        return cred

    def update_score(
        self,
        reviewer_id: str,
        new_score: float,
        correct_decision: bool = None
    ) -> ReviewerCredibility:
        """Update credibility score."""
        cred = self.get_or_create(reviewer_id)

        cred.credibility_score = max(0.0, min(1.0, new_score))
        cred.last_review_at = datetime.now()

        if correct_decision is not None:
            cred.outcomes_recorded += 1
            if correct_decision:
                cred.correct_decisions += 1

        self.session.commit()
        self.session.refresh(cred)
        return cred

    def increment_review(self, reviewer_id: str, was_override: bool) -> ReviewerCredibility:
        """Increment review counts."""
        cred = self.get_or_create(reviewer_id)

        cred.total_reviews += 1
        if was_override:
            cred.total_overrides += 1
        cred.last_review_at = datetime.now()

        self.session.commit()
        self.session.refresh(cred)
        return cred

    def flag_reviewer(self, reviewer_id: str, reason: str) -> ReviewerCredibility:
        """Flag a reviewer for anomalous behavior."""
        cred = self.get_or_create(reviewer_id)

        cred.flagged = True
        cred.flag_reason = reason
        cred.flagged_at = datetime.now()

        self.session.commit()
        self.session.refresh(cred)

        logger.warning(f"Flagged reviewer {reviewer_id}: {reason}")
        return cred

    def unflag_reviewer(self, reviewer_id: str) -> ReviewerCredibility:
        """Remove flag from reviewer."""
        cred = self.get_or_create(reviewer_id)

        cred.flagged = False
        cred.flag_reason = None
        cred.flagged_at = None

        self.session.commit()
        self.session.refresh(cred)
        return cred

    def list_flagged(self) -> List[ReviewerCredibility]:
        """List all flagged reviewers."""
        return self.session.query(ReviewerCredibility).filter(
            ReviewerCredibility.flagged == True
        ).all()

    def list_all(self, limit: int = 100) -> List[ReviewerCredibility]:
        """List all reviewer credibility records."""
        return self.session.query(ReviewerCredibility).order_by(
            desc(ReviewerCredibility.total_reviews)
        ).limit(limit).all()


class ParameterVersionRepository:
    """Repository for versioned learning parameters."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, params_data: Dict[str, Any]) -> ParameterVersion:
        """Create a new parameter version."""
        # Get next version number
        latest = self.get_latest()
        next_version = (latest.version + 1) if latest else 1

        params = ParameterVersion(
            version=next_version,
            **params_data
        )
        self.session.add(params)
        self.session.commit()
        self.session.refresh(params)

        logger.info(f"Created parameter version {next_version}")
        return params

    def get_latest(self) -> Optional[ParameterVersion]:
        """Get the latest parameter version."""
        return self.session.query(ParameterVersion).order_by(
            desc(ParameterVersion.version)
        ).first()

    def get_by_version(self, version: int) -> Optional[ParameterVersion]:
        """Get parameters by version number."""
        return self.session.query(ParameterVersion).filter(
            ParameterVersion.version == version
        ).first()

    def list_all(self, limit: int = 50) -> List[ParameterVersion]:
        """List all parameter versions."""
        return self.session.query(ParameterVersion).order_by(
            desc(ParameterVersion.version)
        ).limit(limit).all()


class LearningRunRepository:
    """Repository for learning run audit trail."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, run_data: Dict[str, Any]) -> LearningRun:
        """Create a new learning run record."""
        run = LearningRun(**run_data)
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)

        logger.info(f"Created learning run: {run.run_id}")
        return run

    def update_status(
        self,
        run_id: str,
        status: str,
        error_message: str = None
    ) -> Optional[LearningRun]:
        """Update learning run status."""
        run = self.session.query(LearningRun).filter(
            LearningRun.run_id == run_id
        ).first()

        if run:
            run.status = status
            if error_message:
                run.error_message = error_message
            if status in ['completed', 'failed', 'rolled_back']:
                run.completed_at = datetime.now()
            self.session.commit()
            self.session.refresh(run)

        return run

    def get_by_id(self, run_id: str) -> Optional[LearningRun]:
        """Get learning run by ID."""
        return self.session.query(LearningRun).filter(
            LearningRun.run_id == run_id
        ).first()

    def list_recent(self, limit: int = 20) -> List[LearningRun]:
        """List recent learning runs."""
        return self.session.query(LearningRun).order_by(
            desc(LearningRun.started_at)
        ).limit(limit).all()


# Convenience class to group all repositories

class UnitOfWork:
    """
    Unit of Work pattern - groups repositories with shared session.
    
    Usage:
        with UnitOfWork(session) as uow:
            decision = uow.decisions.create(...)
            uow.model_decisions.create_bulk(...)
            uow.commit()
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.decisions = DecisionRepository(session)
        self.model_decisions = ModelDecisionRepository(session)
        self.bias_analyses = BiasAnalysisRepository(session)
        self.audit_logs = AuditLogRepository(session)
        self.provider_health = ProviderHealthRepository(session)
        # Phase 3: Feedback & Learning
        self.human_feedback = HumanFeedbackRepository(session)
        self.reviewer_credibility = ReviewerCredibilityRepository(session)
        self.parameter_versions = ParameterVersionRepository(session)
        self.learning_runs = LearningRunRepository(session)
    
    def commit(self):
        """Commit all changes."""
        self.session.commit()
    
    def rollback(self):
        """Rollback all changes."""
        self.session.rollback()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        self.session.close()

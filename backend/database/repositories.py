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
    Decision, ModelDecision, BiasAnalysis, AuditLog, ProviderHealth
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

"""
Database package for TrustChain.

Provides SQLAlchemy models, repositories, and connection management.
"""

from database.models import (
    Base,
    Decision,
    ModelDecision,
    BiasAnalysis,
    AuditLog,
    ProviderHealth,
    User
)

from database.repositories import (
    DecisionRepository,
    ModelDecisionRepository,
    BiasAnalysisRepository,
    AuditLogRepository,
    ProviderHealthRepository,
    UnitOfWork
)

from database.connection import (
    DatabaseManager,
    init_database,
    get_db_manager,
    get_db
)

__all__ = [
    # Models
    "Base",
    "Decision",
    "ModelDecision",
    "BiasAnalysis",
    "AuditLog",
    "ProviderHealth",
    "User",
    
    # Repositories
    "DecisionRepository",
    "ModelDecisionRepository",
    "BiasAnalysisRepository",
    "AuditLogRepository",
    "ProviderHealthRepository",
    "UnitOfWork",
    
    # Connection
    "DatabaseManager",
    "init_database",
    "get_db_manager",
    "get_db",
]

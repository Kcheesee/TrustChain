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
    User,
    # Phase 3: Feedback & Learning
    HumanFeedback,
    ReviewerCredibility,
    ParameterVersion,
    LearningRun,
)

from database.repositories import (
    DecisionRepository,
    ModelDecisionRepository,
    BiasAnalysisRepository,
    AuditLogRepository,
    ProviderHealthRepository,
    # Phase 3: Feedback & Learning
    HumanFeedbackRepository,
    ReviewerCredibilityRepository,
    ParameterVersionRepository,
    LearningRunRepository,
    UnitOfWork,
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
    # Phase 3: Feedback & Learning
    "HumanFeedback",
    "ReviewerCredibility",
    "ParameterVersion",
    "LearningRun",

    # Repositories
    "DecisionRepository",
    "ModelDecisionRepository",
    "BiasAnalysisRepository",
    "AuditLogRepository",
    "ProviderHealthRepository",
    # Phase 3: Feedback & Learning
    "HumanFeedbackRepository",
    "ReviewerCredibilityRepository",
    "ParameterVersionRepository",
    "LearningRunRepository",
    "UnitOfWork",

    # Connection
    "DatabaseManager",
    "init_database",
    "get_db_manager",
    "get_db",
]

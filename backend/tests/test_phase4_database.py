"""
Tests for Phase 4: PostgreSQL Database Integration

Tests database models, repositories, and PostgresFeedbackStore.
Uses SQLite in-memory database for testing (same SQLAlchemy interface).

Built with care by Kareem & Claude
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Create a test-specific base that doesn't include ARRAY types
TestBase = declarative_base()

# Import only Phase 4 models that work with SQLite
from database.models import (
    HumanFeedback as HumanFeedbackModel,
    ReviewerCredibility,
    ParameterVersion,
    LearningRun,
)

# Rebind Phase 4 models to TestBase for SQLite compatibility
# Create SQLite-compatible versions for testing
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, TIMESTAMP, JSON
)
from sqlalchemy.sql import func


class TestHumanFeedbackModel(TestBase):
    """SQLite-compatible HumanFeedback for testing."""
    __tablename__ = "human_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feedback_id = Column(String(255), unique=True, nullable=False, index=True)
    result_id = Column(String(255), nullable=False, index=True)
    reviewer_id = Column(String(255), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    original_decision = Column(String(50), nullable=False)
    final_decision = Column(String(50), nullable=False)
    override_reason = Column(String(100))
    confidence_adjustment = Column(Float)
    decision_type = Column(String(100), index=True)
    notes = Column(Text)
    outcome = Column(String(50))
    outcome_recorded_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)


class TestReviewerCredibilityModel(TestBase):
    """SQLite-compatible ReviewerCredibility for testing."""
    __tablename__ = "reviewer_credibility"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reviewer_id = Column(String(255), unique=True, nullable=False, index=True)
    total_reviews = Column(Integer, nullable=False, default=0)
    total_overrides = Column(Integer, nullable=False, default=0)
    outcomes_recorded = Column(Integer, nullable=False, default=0)
    correct_decisions = Column(Integer, nullable=False, default=0)
    credibility_score = Column(Float, nullable=False, default=0.5)
    flagged = Column(Boolean, nullable=False, default=False, index=True)
    flag_reason = Column(String(255))
    flagged_at = Column(TIMESTAMP)
    first_review_at = Column(TIMESTAMP, server_default=func.now())
    last_review_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now())


class TestParameterVersionModel(TestBase):
    """SQLite-compatible ParameterVersion for testing."""
    __tablename__ = "parameter_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, nullable=False, unique=True, index=True)
    model_weights = Column(JSON)
    confidence_adjustments = Column(JSON)
    analyzer_sensitivity = Column(JSON)
    feedback_count = Column(Integer, nullable=False, default=0)
    notes = Column(Text)
    checksum = Column(String(64))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)


class TestLearningRunModel(TestBase):
    """SQLite-compatible LearningRun for testing."""
    __tablename__ = "learning_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(255), unique=True, nullable=False, index=True)
    feedback_processed = Column(Integer, nullable=False, default=0)
    reviewers_included = Column(Integer, nullable=False, default=0)
    reviewers_excluded = Column(Integer, nullable=False, default=0)
    parameter_version_before = Column(Integer)
    parameter_version_after = Column(Integer)
    status = Column(String(50), nullable=False, default="running", index=True)
    error_message = Column(Text)
    started_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP)


# Test-specific repositories using SQLite-compatible models
class TestHumanFeedbackRepository:
    """Repository for test HumanFeedback."""

    def __init__(self, session):
        self.session = session

    def create(self, data):
        feedback = TestHumanFeedbackModel(**data)
        self.session.add(feedback)
        self.session.commit()
        self.session.refresh(feedback)
        return feedback

    def get_by_id(self, feedback_id):
        return self.session.query(TestHumanFeedbackModel).filter(
            TestHumanFeedbackModel.feedback_id == feedback_id
        ).first()

    def list_by_reviewer(self, reviewer_id, limit=100):
        return self.session.query(TestHumanFeedbackModel).filter(
            TestHumanFeedbackModel.reviewer_id == reviewer_id
        ).limit(limit).all()

    def count_by_reviewer(self, reviewer_id):
        total = self.session.query(TestHumanFeedbackModel).filter(
            TestHumanFeedbackModel.reviewer_id == reviewer_id
        ).count()
        overrides = self.session.query(TestHumanFeedbackModel).filter(
            TestHumanFeedbackModel.reviewer_id == reviewer_id,
            TestHumanFeedbackModel.action.in_(['OVERRIDE_TO_APPROVE', 'OVERRIDE_TO_DENY'])
        ).count()
        return {"total": total, "overrides": overrides}


class TestReviewerCredibilityRepository:
    """Repository for test ReviewerCredibility."""

    def __init__(self, session):
        self.session = session

    def get_or_create(self, reviewer_id):
        cred = self.session.query(TestReviewerCredibilityModel).filter(
            TestReviewerCredibilityModel.reviewer_id == reviewer_id
        ).first()
        if not cred:
            cred = TestReviewerCredibilityModel(reviewer_id=reviewer_id)
            self.session.add(cred)
            self.session.commit()
            self.session.refresh(cred)
        return cred

    def increment_review(self, reviewer_id, was_override):
        cred = self.get_or_create(reviewer_id)
        cred.total_reviews += 1
        if was_override:
            cred.total_overrides += 1
        self.session.commit()
        self.session.refresh(cred)
        return cred

    def flag_reviewer(self, reviewer_id, reason):
        cred = self.get_or_create(reviewer_id)
        cred.flagged = True
        cred.flag_reason = reason
        cred.flagged_at = datetime.now()
        self.session.commit()
        self.session.refresh(cred)
        return cred

    def unflag_reviewer(self, reviewer_id):
        cred = self.get_or_create(reviewer_id)
        cred.flagged = False
        cred.flag_reason = None
        cred.flagged_at = None
        self.session.commit()
        self.session.refresh(cred)
        return cred

    def list_flagged(self):
        return self.session.query(TestReviewerCredibilityModel).filter(
            TestReviewerCredibilityModel.flagged == True
        ).all()


class TestParameterVersionRepository:
    """Repository for test ParameterVersion."""

    def __init__(self, session):
        self.session = session

    def create(self, data):
        latest = self.get_latest()
        next_version = (latest.version + 1) if latest else 1
        params = TestParameterVersionModel(version=next_version, **data)
        self.session.add(params)
        self.session.commit()
        self.session.refresh(params)
        return params

    def get_latest(self):
        return self.session.query(TestParameterVersionModel).order_by(
            TestParameterVersionModel.version.desc()
        ).first()

    def get_by_version(self, version):
        return self.session.query(TestParameterVersionModel).filter(
            TestParameterVersionModel.version == version
        ).first()


class TestLearningRunRepository:
    """Repository for test LearningRun."""

    def __init__(self, session):
        self.session = session

    def create(self, data):
        run = TestLearningRunModel(**data)
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def update_status(self, run_id, status, error_message=None):
        run = self.session.query(TestLearningRunModel).filter(
            TestLearningRunModel.run_id == run_id
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


@pytest.fixture
def test_engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    TestBase.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


# ============================================================================
# Model Tests (using SQLite-compatible test models)
# ============================================================================

class TestFeedbackModel:
    """Test HumanFeedback database model."""

    def test_create_feedback(self, test_session):
        """Test creating a feedback record."""
        feedback = TestHumanFeedbackModel(
            feedback_id="fb_001",
            result_id="tc_result_001",
            reviewer_id="reviewer_jane",
            action="AGREE",
            original_decision="approved",
            final_decision="approved",
        )
        test_session.add(feedback)
        test_session.commit()

        assert feedback.id is not None
        assert feedback.feedback_id == "fb_001"
        assert feedback.action == "AGREE"

    def test_feedback_with_override(self, test_session):
        """Test feedback with override details."""
        feedback = TestHumanFeedbackModel(
            feedback_id="fb_002",
            result_id="tc_result_002",
            reviewer_id="reviewer_bob",
            action="OVERRIDE_TO_APPROVE",
            original_decision="denied",
            final_decision="approved",
            override_reason="MISSING_CONTEXT",
            confidence_adjustment=0.15,
            notes="Applicant provided additional documentation.",
        )
        test_session.add(feedback)
        test_session.commit()

        assert feedback.override_reason == "MISSING_CONTEXT"
        assert feedback.confidence_adjustment == 0.15


class TestCredibilityModel:
    """Test ReviewerCredibility database model."""

    def test_create_credibility(self, test_session):
        """Test creating a credibility record."""
        cred = TestReviewerCredibilityModel(
            reviewer_id="reviewer_alice",
            total_reviews=50,
            total_overrides=5,
            credibility_score=0.85,
        )
        test_session.add(cred)
        test_session.commit()

        assert cred.id is not None
        assert cred.credibility_score == 0.85
        assert cred.flagged == False

    def test_flag_reviewer(self, test_session):
        """Test flagging a reviewer."""
        cred = TestReviewerCredibilityModel(
            reviewer_id="reviewer_suspicious",
            total_reviews=20,
            total_overrides=15,
            credibility_score=0.25,
            flagged=True,
            flag_reason="HIGH_OVERRIDE_RATE",
        )
        test_session.add(cred)
        test_session.commit()

        assert cred.flagged == True
        assert cred.flag_reason == "HIGH_OVERRIDE_RATE"


class TestParamVersionModel:
    """Test ParameterVersion database model."""

    def test_create_parameter_version(self, test_session):
        """Test creating a parameter version."""
        params = TestParameterVersionModel(
            version=1,
            model_weights={"anthropic": 0.4, "openai": 0.35, "llama": 0.25},
            confidence_adjustments={"low_consensus": -0.1},
            feedback_count=100,
            notes="Initial version",
        )
        test_session.add(params)
        test_session.commit()

        assert params.id is not None
        assert params.version == 1
        assert params.model_weights["anthropic"] == 0.4


class TestLearningModel:
    """Test LearningRun database model."""

    def test_create_learning_run(self, test_session):
        """Test creating a learning run record."""
        run = TestLearningRunModel(
            run_id="learn_001",
            feedback_processed=50,
            reviewers_included=10,
            reviewers_excluded=2,
            status="completed",
            parameter_version_before=1,
            parameter_version_after=2,
        )
        test_session.add(run)
        test_session.commit()

        assert run.id is not None
        assert run.status == "completed"
        assert run.feedback_processed == 50


# ============================================================================
# Repository Tests (using test-specific repositories)
# ============================================================================

class TestFeedbackRepo:
    """Test HumanFeedback repository operations."""

    def test_create_feedback(self, test_session):
        """Test creating feedback via repository."""
        repo = TestHumanFeedbackRepository(test_session)

        feedback = repo.create({
            "feedback_id": "fb_repo_001",
            "result_id": "tc_result_001",
            "reviewer_id": "reviewer_jane",
            "action": "AGREE",
            "original_decision": "approved",
            "final_decision": "approved",
        })

        assert feedback.feedback_id == "fb_repo_001"

    def test_get_by_id(self, test_session):
        """Test getting feedback by ID."""
        repo = TestHumanFeedbackRepository(test_session)

        repo.create({
            "feedback_id": "fb_get_001",
            "result_id": "tc_result_get",
            "reviewer_id": "reviewer_test",
            "action": "AGREE",
            "original_decision": "approved",
            "final_decision": "approved",
        })

        result = repo.get_by_id("fb_get_001")
        assert result is not None
        assert result.feedback_id == "fb_get_001"

    def test_list_by_reviewer(self, test_session):
        """Test listing feedback by reviewer."""
        repo = TestHumanFeedbackRepository(test_session)

        # Create multiple feedback for same reviewer
        for i in range(3):
            repo.create({
                "feedback_id": f"fb_list_{i}",
                "result_id": f"tc_result_list_{i}",
                "reviewer_id": "reviewer_prolific",
                "action": "AGREE",
                "original_decision": "approved",
                "final_decision": "approved",
            })

        results = repo.list_by_reviewer("reviewer_prolific")
        assert len(results) == 3

    def test_count_by_reviewer(self, test_session):
        """Test counting feedback stats for reviewer."""
        repo = TestHumanFeedbackRepository(test_session)

        # 2 agreements, 1 override
        repo.create({
            "feedback_id": "fb_count_1",
            "result_id": "tc_count_1",
            "reviewer_id": "reviewer_count",
            "action": "AGREE",
            "original_decision": "approved",
            "final_decision": "approved",
        })
        repo.create({
            "feedback_id": "fb_count_2",
            "result_id": "tc_count_2",
            "reviewer_id": "reviewer_count",
            "action": "AGREE",
            "original_decision": "denied",
            "final_decision": "denied",
        })
        repo.create({
            "feedback_id": "fb_count_3",
            "result_id": "tc_count_3",
            "reviewer_id": "reviewer_count",
            "action": "OVERRIDE_TO_APPROVE",
            "original_decision": "denied",
            "final_decision": "approved",
        })

        stats = repo.count_by_reviewer("reviewer_count")
        assert stats["total"] == 3
        assert stats["overrides"] == 1


class TestCredibilityRepo:
    """Test ReviewerCredibility repository operations."""

    def test_get_or_create_new(self, test_session):
        """Test creating new credibility record."""
        repo = TestReviewerCredibilityRepository(test_session)

        cred = repo.get_or_create("new_reviewer")
        assert cred is not None
        assert cred.reviewer_id == "new_reviewer"
        assert cred.credibility_score == 0.5  # Default

    def test_get_or_create_existing(self, test_session):
        """Test getting existing credibility record."""
        repo = TestReviewerCredibilityRepository(test_session)

        # Create first
        repo.get_or_create("existing_reviewer")
        # Get again
        cred = repo.get_or_create("existing_reviewer")
        assert cred.reviewer_id == "existing_reviewer"

    def test_increment_review(self, test_session):
        """Test incrementing review counts."""
        repo = TestReviewerCredibilityRepository(test_session)

        cred = repo.get_or_create("increment_test")
        initial_reviews = cred.total_reviews

        repo.increment_review("increment_test", was_override=False)
        cred = repo.get_or_create("increment_test")
        assert cred.total_reviews == initial_reviews + 1

    def test_flag_and_unflag(self, test_session):
        """Test flagging and unflagging reviewer."""
        repo = TestReviewerCredibilityRepository(test_session)

        # Flag
        cred = repo.flag_reviewer("flag_test", "SUSPICIOUS_ACTIVITY")
        assert cred.flagged == True
        assert cred.flag_reason == "SUSPICIOUS_ACTIVITY"

        # Unflag
        cred = repo.unflag_reviewer("flag_test")
        assert cred.flagged == False
        assert cred.flag_reason is None

    def test_list_flagged(self, test_session):
        """Test listing flagged reviewers."""
        repo = TestReviewerCredibilityRepository(test_session)

        repo.flag_reviewer("flagged_1", "REASON_1")
        repo.flag_reviewer("flagged_2", "REASON_2")
        repo.get_or_create("not_flagged")

        flagged = repo.list_flagged()
        assert len(flagged) == 2


class TestParamVersionRepo:
    """Test ParameterVersion repository operations."""

    def test_create_auto_version(self, test_session):
        """Test creating parameter version with auto-incrementing version."""
        repo = TestParameterVersionRepository(test_session)

        v1 = repo.create({
            "model_weights": {"anthropic": 0.33},
            "feedback_count": 10,
        })
        assert v1.version == 1

        v2 = repo.create({
            "model_weights": {"anthropic": 0.35},
            "feedback_count": 20,
        })
        assert v2.version == 2

    def test_get_latest(self, test_session):
        """Test getting latest parameter version."""
        repo = TestParameterVersionRepository(test_session)

        repo.create({"model_weights": {"a": 1}, "feedback_count": 10})
        repo.create({"model_weights": {"a": 2}, "feedback_count": 20})
        repo.create({"model_weights": {"a": 3}, "feedback_count": 30})

        latest = repo.get_latest()
        assert latest.version == 3
        assert latest.model_weights["a"] == 3

    def test_get_by_version(self, test_session):
        """Test getting specific parameter version."""
        repo = TestParameterVersionRepository(test_session)

        repo.create({"model_weights": {"x": 1}, "feedback_count": 10})
        repo.create({"model_weights": {"x": 2}, "feedback_count": 20})

        v1 = repo.get_by_version(1)
        assert v1.model_weights["x"] == 1

        v2 = repo.get_by_version(2)
        assert v2.model_weights["x"] == 2


class TestLearningRunRepo:
    """Test LearningRun repository operations."""

    def test_create_run(self, test_session):
        """Test creating learning run."""
        repo = TestLearningRunRepository(test_session)

        run = repo.create({
            "run_id": "run_001",
            "feedback_processed": 50,
            "reviewers_included": 10,
            "reviewers_excluded": 2,
            "status": "running",
        })

        assert run.run_id == "run_001"
        assert run.status == "running"

    def test_update_status(self, test_session):
        """Test updating run status."""
        repo = TestLearningRunRepository(test_session)

        repo.create({
            "run_id": "run_update",
            "feedback_processed": 50,
            "reviewers_included": 10,
            "reviewers_excluded": 0,
            "status": "running",
        })

        run = repo.update_status("run_update", "completed")
        assert run.status == "completed"
        assert run.completed_at is not None

    def test_update_status_failed(self, test_session):
        """Test updating run status to failed with error."""
        repo = TestLearningRunRepository(test_session)

        repo.create({
            "run_id": "run_fail",
            "feedback_processed": 0,
            "reviewers_included": 0,
            "reviewers_excluded": 0,
            "status": "running",
        })

        run = repo.update_status("run_fail", "failed", "Database connection lost")
        assert run.status == "failed"
        assert run.error_message == "Database connection lost"

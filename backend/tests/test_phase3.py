"""
Phase 3: Feedback & Learning System Tests

Tests for the human feedback capture, storage, and learning engine
that enables TrustChain to improve from human reviewer decisions.

Built with care by Kareem & Claude
"""
import pytest
from datetime import datetime, timedelta

# Feedback module imports
from feedback import (
    ReviewerAction,
    OverrideReason,
    HumanFeedback,
    FeedbackStats,
    InMemoryFeedbackStore,
)

# Learning module imports
from learning import (
    LearnedParameters,
    LearningEngine,
    LearningGuard,
    ReviewerCredibility,
    AnomalyType,
)


# ============================================================================
# FEEDBACK CAPTURE TESTS
# ============================================================================

class TestReviewerAction:
    """Tests for ReviewerAction enum and helper properties."""

    def test_agreement_actions(self):
        """Test is_agreement property identifies correct actions."""
        assert ReviewerAction.AGREE_APPROVE.is_agreement is True
        assert ReviewerAction.AGREE_DENY.is_agreement is True
        assert ReviewerAction.AGREE_FLAG.is_agreement is True

    def test_override_actions(self):
        """Test is_override property identifies correct actions."""
        assert ReviewerAction.OVERRIDE_TO_APPROVE.is_override is True
        assert ReviewerAction.OVERRIDE_TO_DENY.is_override is True

    def test_escalation_action(self):
        """Test escalate action is neither agreement nor override."""
        assert ReviewerAction.ESCALATE.is_agreement is False
        assert ReviewerAction.ESCALATE.is_override is False

    def test_all_values_unique(self):
        """Ensure all enum values are unique."""
        values = [a.value for a in ReviewerAction]
        assert len(values) == len(set(values))


class TestOverrideReason:
    """Tests for OverrideReason enum."""

    def test_common_reasons_exist(self):
        """Test common override reasons are defined."""
        assert hasattr(OverrideReason, 'CONTEXT_NOT_CAPTURED')
        assert hasattr(OverrideReason, 'FALSE_POSITIVE_BIAS')
        assert hasattr(OverrideReason, 'FALSE_NEGATIVE_BIAS')
        assert hasattr(OverrideReason, 'POLICY_EXCEPTION')
        assert hasattr(OverrideReason, 'MODEL_HALLUCINATION')


class TestHumanFeedback:
    """Tests for HumanFeedback dataclass."""

    def test_create_agreement_feedback(self):
        """Test creating feedback for agreement case."""
        feedback = HumanFeedback(
            result_id="tc_123",
            case_id="case_456",
            reviewer_id="jane_hr",
            action=ReviewerAction.AGREE_APPROVE,
            reasoning="Decision looks correct"
        )

        assert feedback.result_id == "tc_123"
        assert feedback.case_id == "case_456"
        assert feedback.reviewer_id == "jane_hr"
        assert feedback.action == ReviewerAction.AGREE_APPROVE
        assert feedback.action.is_agreement is True
        assert feedback.feedback_id != ""
        assert feedback.timestamp is not None

    def test_create_override_feedback(self):
        """Test creating feedback for override case."""
        feedback = HumanFeedback(
            result_id="tc_789",
            case_id="case_012",
            reviewer_id="bob_compliance",
            action=ReviewerAction.OVERRIDE_TO_DENY,
            reasoning="Model missed critical information",
            override_reason=OverrideReason.CONTEXT_NOT_CAPTURED,
            incorrect_flags=["culture_fit"],
            missed_flags=["graduation_year"]
        )

        assert feedback.action == ReviewerAction.OVERRIDE_TO_DENY
        assert feedback.action.is_override is True
        assert feedback.override_reason == OverrideReason.CONTEXT_NOT_CAPTURED
        assert "culture_fit" in feedback.incorrect_flags
        assert "graduation_year" in feedback.missed_flags

    def test_feedback_id_generation(self):
        """Test that feedback IDs are unique."""
        feedback1 = HumanFeedback(
            result_id="tc_1",
            case_id="case_1",
            reviewer_id="reviewer_1",
            action=ReviewerAction.AGREE_APPROVE
        )
        feedback2 = HumanFeedback(
            result_id="tc_2",
            case_id="case_2",
            reviewer_id="reviewer_2",
            action=ReviewerAction.AGREE_APPROVE
        )

        assert feedback1.feedback_id != feedback2.feedback_id

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        feedback = HumanFeedback(
            result_id="tc_123",
            case_id="case_456",
            reviewer_id="jane_hr",
            action=ReviewerAction.OVERRIDE_TO_APPROVE,
            reasoning="Policy exception applies",
            override_reason=OverrideReason.POLICY_EXCEPTION
        )

        d = feedback.to_dict()

        assert d["result_id"] == "tc_123"
        assert d["action"] == "override_approve"
        assert d["override_reason"] == "policy_exception"
        assert "feedback_id" in d
        assert "timestamp" in d


# ============================================================================
# FEEDBACK STORAGE TESTS
# ============================================================================

class TestInMemoryFeedbackStore:
    """Tests for InMemoryFeedbackStore implementation."""

    @pytest.fixture
    def store(self):
        """Create fresh in-memory store for each test."""
        return InMemoryFeedbackStore()

    @pytest.fixture
    def sample_feedback(self):
        """Create sample feedback objects."""
        return [
            HumanFeedback(
                result_id="tc_001",
                case_id="case_001",
                reviewer_id="reviewer_a",
                action=ReviewerAction.AGREE_APPROVE,
                reasoning="Looks good"
            ),
            HumanFeedback(
                result_id="tc_002",
                case_id="case_002",
                reviewer_id="reviewer_a",
                action=ReviewerAction.OVERRIDE_TO_DENY,
                reasoning="Missing context",
                override_reason=OverrideReason.CONTEXT_NOT_CAPTURED
            ),
            HumanFeedback(
                result_id="tc_003",
                case_id="case_003",
                reviewer_id="reviewer_b",
                action=ReviewerAction.AGREE_DENY,
                reasoning="Correct denial"
            ),
        ]

    @pytest.mark.asyncio
    async def test_save_feedback(self, store):
        """Test saving feedback to store."""
        feedback = HumanFeedback(
            result_id="tc_test",
            case_id="case_test",
            reviewer_id="reviewer_test",
            action=ReviewerAction.AGREE_APPROVE
        )

        await store.save_feedback(feedback)
        retrieved = await store.get_feedback_for_result("tc_test")

        assert retrieved is not None
        assert retrieved.result_id == "tc_test"

    @pytest.mark.asyncio
    async def test_get_feedback_by_result_id(self, store, sample_feedback):
        """Test retrieving feedback by result ID."""
        for f in sample_feedback:
            await store.save_feedback(f)

        retrieved = await store.get_feedback_for_result("tc_002")

        assert retrieved is not None
        assert retrieved.action == ReviewerAction.OVERRIDE_TO_DENY

    @pytest.mark.asyncio
    async def test_get_feedback_batch_by_reviewer(self, store, sample_feedback):
        """Test retrieving feedback batch by reviewer ID."""
        for f in sample_feedback:
            await store.save_feedback(f)

        retrieved = await store.get_feedback_batch(reviewer_id="reviewer_a")

        assert len(retrieved) == 2

    @pytest.mark.asyncio
    async def test_compute_stats(self, store, sample_feedback):
        """Test computing aggregate statistics."""
        for f in sample_feedback:
            await store.save_feedback(f)

        stats = await store.compute_stats()

        assert stats.total_reviewed == 3
        # 2 agreements (AGREE_APPROVE, AGREE_DENY) out of 3
        assert stats.agreement_rate == pytest.approx(2/3, rel=0.01)
        # 1 override out of 3
        assert stats.override_rate == pytest.approx(1/3, rel=0.01)

    @pytest.mark.asyncio
    async def test_update_outcome(self, store, sample_feedback):
        """Test updating feedback with long-term outcome."""
        await store.save_feedback(sample_feedback[0])

        result = await store.update_outcome(
            result_id="tc_001",
            final_outcome="successful_hire",
            outcome_timestamp=datetime.now(),
            notes="Good performance"
        )

        assert result is True

        retrieved = await store.get_feedback_for_result("tc_001")
        assert retrieved.final_outcome == "successful_hire"
        assert retrieved.outcome_tracked is True


# ============================================================================
# LEARNING ENGINE TESTS
# ============================================================================

class TestLearningEngine:
    """Tests for LearningEngine."""

    @pytest.fixture
    def store(self):
        """Create in-memory feedback store."""
        return InMemoryFeedbackStore()

    @pytest.fixture
    def engine(self, store):
        """Create learning engine with store."""
        return LearningEngine(
            feedback_store=store,
            learning_rate=0.1,
            min_feedback_count=5
        )

    def test_engine_initialization(self, engine):
        """Test engine initializes with correct parameters."""
        assert engine.learning_rate == 0.1
        assert engine.min_feedback == 5

    @pytest.mark.asyncio
    async def test_learn_insufficient_feedback(self, engine, store):
        """Test learning skips when insufficient feedback."""
        # Only 3 feedback items (below minimum of 5)
        for i in range(3):
            feedback = HumanFeedback(
                result_id=f"tc_{i}",
                case_id=f"case_{i}",
                reviewer_id="reviewer",
                action=ReviewerAction.AGREE_APPROVE
            )
            await store.save_feedback(feedback)

        results = await engine.learn()

        assert results["status"] == "insufficient_data"

    @pytest.mark.asyncio
    async def test_learn_with_sufficient_feedback(self, engine, store):
        """Test learning processes feedback when sufficient."""
        # Create 10 feedback items
        for i in range(10):
            action = ReviewerAction.AGREE_APPROVE if i % 2 == 0 else ReviewerAction.OVERRIDE_TO_DENY
            feedback = HumanFeedback(
                result_id=f"tc_{i}",
                case_id=f"case_{i}",
                reviewer_id="reviewer",
                action=action,
            )
            await store.save_feedback(feedback)

        results = await engine.learn(force=True)

        assert results["status"] == "success"
        assert results["feedback_count"] >= 5

    def test_get_parameters_empty(self, engine):
        """Test getting parameters with no learning done."""
        params = engine.get_parameters()

        assert isinstance(params, LearnedParameters)
        assert params.feedback_count == 0

    def test_register_and_get_model_weights(self, engine):
        """Test registering models and getting their weights."""
        engine.register_model("anthropic", base_weight=1.0)
        engine.register_model("openai", base_weight=0.9)

        params = engine.get_parameters()

        assert "anthropic" in params.model_weights
        assert "openai" in params.model_weights


class TestLearnedParameters:
    """Tests for LearnedParameters dataclass."""

    def test_empty_parameters(self):
        """Test creating empty parameters."""
        params = LearnedParameters()

        assert params.model_weights == {}
        assert params.analyzer_sensitivity == {}
        assert params.feedback_count == 0

    def test_parameters_with_values(self):
        """Test creating parameters with learned values."""
        params = LearnedParameters(
            model_weights={
                "anthropic": 1.2,
                "openai": 0.9,
            },
            analyzer_sensitivity={
                "proxy_variables": 0.1,
            },
            feedback_count=100
        )

        assert len(params.model_weights) == 2
        assert params.model_weights["anthropic"] == 1.2
        assert len(params.analyzer_sensitivity) == 1
        assert params.feedback_count == 100


# ============================================================================
# LEARNING HOOKS TESTS (Analyzer-only, avoiding Python 3.9 issue)
# ============================================================================

class TestProxyVariablesLearningHooks:
    """Tests for learning hooks on ProxyVariablesAnalyzer."""

    def test_adjust_sensitivity_high(self):
        """Test adjusting sensitivity upward."""
        from analyzers import ProxyVariablesAnalyzer

        analyzer = ProxyVariablesAnalyzer(config={"sensitivity": "medium"})

        analyzer.adjust_sensitivity(1.5)  # High multiplier

        assert analyzer.get_sensitivity() == "high"

    def test_adjust_sensitivity_low(self):
        """Test adjusting sensitivity downward."""
        from analyzers import ProxyVariablesAnalyzer

        analyzer = ProxyVariablesAnalyzer(config={"sensitivity": "medium"})

        analyzer.adjust_sensitivity(0.7)  # Low multiplier

        assert analyzer.get_sensitivity() == "low"

    def test_adjust_sensitivity_unchanged(self):
        """Test sensitivity stays medium with moderate multiplier."""
        from analyzers import ProxyVariablesAnalyzer

        analyzer = ProxyVariablesAnalyzer(config={"sensitivity": "medium"})

        analyzer.adjust_sensitivity(1.0)  # Neutral multiplier

        assert analyzer.get_sensitivity() == "medium"


class TestProtectedAttributesLearningHooks:
    """Tests for learning hooks on ProtectedAttributesAnalyzer."""

    def test_adjust_sensitivity_threshold(self):
        """Test adjusting confidence threshold via sensitivity."""
        from analyzers import ProtectedAttributesAnalyzer

        analyzer = ProtectedAttributesAnalyzer(config={"confidence_threshold": 0.7})

        # Higher multiplier = lower threshold (more strict)
        analyzer.adjust_sensitivity(1.4)

        settings = analyzer.get_sensitivity_settings()
        assert settings["confidence_threshold"] < 0.7

    def test_adjust_sensitivity_strict_mode(self):
        """Test that high multiplier enables strict mode."""
        from analyzers import ProtectedAttributesAnalyzer

        analyzer = ProtectedAttributesAnalyzer(config={"strict_mode": False})

        analyzer.adjust_sensitivity(1.5)

        settings = analyzer.get_sensitivity_settings()
        assert settings["strict_mode"] is True


# ============================================================================
# SAFEGUARDS TESTS (Bad Actor Protection)
# ============================================================================

class TestLearningGuard:
    """Tests for LearningGuard bad actor protection."""

    @pytest.fixture
    def guard(self):
        """Create fresh LearningGuard."""
        return LearningGuard(
            max_reviewer_influence=0.15,
            min_credibility_for_learning=0.3,
            anomaly_override_threshold=0.4
        )

    def test_new_reviewer_gets_partial_weight(self, guard):
        """New reviewers get partial weight until we have data."""
        weight = guard.get_reviewer_weight("new_reviewer")
        assert weight == 0.5  # Default for unknown

    def test_record_review_updates_credibility(self, guard):
        """Recording reviews updates reviewer credibility."""
        guard.record_review("reviewer_a", was_override=False)
        guard.record_review("reviewer_a", was_override=True, override_flag_type="proxy_variables")
        guard.record_review("reviewer_a", was_override=False)

        cred = guard.reviewer_credibility["reviewer_a"]
        assert cred.total_reviews == 3
        assert cred.total_overrides == 1
        assert cred.override_by_type.get("proxy_variables") == 1

    def test_high_override_rate_triggers_anomaly(self, guard):
        """High override rate triggers anomaly detection."""
        # Simulate reviewer who overrides 80% of the time
        for i in range(10):
            guard.record_review("bad_reviewer", was_override=(i < 8))

        cred = guard.reviewer_credibility["bad_reviewer"]
        assert cred.override_rate == 0.8
        assert AnomalyType.HIGH_OVERRIDE_RATE in cred.anomalies_detected

    def test_flagged_reviewer_gets_zero_weight(self, guard):
        """Flagged reviewers get zero weight."""
        guard.reviewer_credibility["flagged_one"] = ReviewerCredibility(
            reviewer_id="flagged_one"
        )
        guard.reviewer_credibility["flagged_one"].flagged_for_review = True

        weight = guard.get_reviewer_weight("flagged_one")
        assert weight == 0.0

    def test_reviewer_caps_applied(self, guard):
        """Single reviewer influence is capped."""
        weights = {
            "reviewer_a": 50.0,  # Too high
            "reviewer_b": 10.0,  # OK
        }

        adjusted = guard.apply_reviewer_caps(weights, total_feedback_count=100)

        # Max influence is 15% of 100 = 15
        assert adjusted["reviewer_a"] == 15.0
        assert adjusted["reviewer_b"] == 10.0

    def test_outcome_updates_credibility(self, guard):
        """Recording outcomes updates credibility score."""
        guard.record_review("reviewer_a", was_override=False)

        # Record outcome - reviewer was correct
        guard.record_outcome(
            feedback_id="fb_1",
            result_id="tc_1",
            reviewer_id="reviewer_a",
            outcome="successful_hire",
            reviewer_decision_correct=True
        )

        cred = guard.reviewer_credibility["reviewer_a"]
        assert cred.total_decisions_with_outcomes == 1
        assert cred.correct_outcomes == 1
        assert cred.outcome_accuracy == 1.0

    def test_safeguards_report(self, guard):
        """Get comprehensive safeguards report."""
        guard.record_review("reviewer_a", was_override=False)
        guard.record_review("reviewer_b", was_override=True)

        report = guard.get_safeguards_report()

        assert report["reviewer_count"] == 2
        assert "settings" in report
        assert report["settings"]["max_reviewer_influence"] == 0.15


class TestReviewerCredibility:
    """Tests for ReviewerCredibility dataclass."""

    def test_credibility_score_no_data(self):
        """New reviewer with no outcome data gets neutral score."""
        cred = ReviewerCredibility(reviewer_id="new_one")

        # No outcome data, so capped at 0.7
        assert cred.credibility_score <= 0.7

    def test_credibility_score_with_outcomes(self):
        """Credibility score based on outcome accuracy."""
        cred = ReviewerCredibility(
            reviewer_id="tested_one",
            total_decisions_with_outcomes=10,
            correct_outcomes=8,  # 80% accuracy
            total_reviews=10,
            total_overrides=1,  # 10% override rate (normal)
        )

        assert cred.outcome_accuracy == 0.8
        # Credibility should be close to accuracy
        assert cred.credibility_score >= 0.7

    def test_high_override_penalty(self):
        """High override rate penalizes credibility."""
        cred = ReviewerCredibility(
            reviewer_id="override_happy",
            total_decisions_with_outcomes=10,
            correct_outcomes=8,  # 80% accuracy
            total_reviews=10,
            total_overrides=6,  # 60% override rate (very high)
        )

        # Should be penalized for high override rate
        assert cred.credibility_score < cred.outcome_accuracy


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestFeedbackLearningIntegration:
    """Integration tests for the feedback-learning loop."""

    @pytest.mark.asyncio
    async def test_full_feedback_loop(self):
        """Test complete flow from feedback to learned parameters."""
        # 1. Create feedback store
        store = InMemoryFeedbackStore()

        # 2. Add feedback simulating real usage
        for i in range(15):
            action = ReviewerAction.AGREE_APPROVE if i % 3 != 0 else ReviewerAction.OVERRIDE_TO_DENY
            feedback = HumanFeedback(
                result_id=f"tc_{i:03d}",
                case_id=f"case_{i:03d}",
                reviewer_id="reviewer_a" if i < 10 else "reviewer_b",
                action=action,
            )
            await store.save_feedback(feedback)

        # 3. Create learning engine and learn
        engine = LearningEngine(
            feedback_store=store,
            learning_rate=0.1,
            min_feedback_count=10
        )

        results = await engine.learn()

        # 4. Verify learning occurred
        assert results["status"] == "success"
        assert results["feedback_count"] >= 10

        # 5. Get learned parameters
        params = engine.get_parameters()

        assert params.feedback_count >= 10

    @pytest.mark.asyncio
    async def test_safeguarded_learning(self):
        """Test learning with safeguards enabled."""
        store = InMemoryFeedbackStore()
        guard = LearningGuard(min_credibility_for_learning=0.3)

        # Add feedback from multiple reviewers
        for i in range(20):
            reviewer = "good_reviewer" if i % 4 != 0 else "suspicious_reviewer"
            feedback = HumanFeedback(
                result_id=f"tc_{i:03d}",
                case_id=f"case_{i:03d}",
                reviewer_id=reviewer,
                action=ReviewerAction.AGREE_APPROVE,
            )
            await store.save_feedback(feedback)
            guard.record_review(reviewer, was_override=False)

        # Flag the suspicious reviewer
        guard.reviewer_credibility["suspicious_reviewer"].flagged_for_review = True
        guard.reviewer_credibility["suspicious_reviewer"].flag_reason = "Test flag"

        # Create engine with safeguards
        engine = LearningEngine(
            feedback_store=store,
            learning_rate=0.1,
            min_feedback_count=10,
            safeguard=guard
        )

        results = await engine.learn()

        # Should succeed but report excluded reviewers
        assert results["status"] == "success"
        assert "safeguards" in results
        assert results["safeguards"]["reviewers_excluded"] >= 1

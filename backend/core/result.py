"""
TrustChain Result Objects

Unified result objects that flow through the TrustChain pipeline:
- StrategyResult: Output from evaluation strategies
- AnalysisResult: Output from analyzer modules
- AccountabilityResult: Complete TrustChain output

Built with care by Kareem & Claude
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import hashlib
import json


class DecisionOutcome(str, Enum):
    """Possible outcomes from an evaluation."""
    APPROVED = "approved"
    DENIED = "denied"
    NEEDS_REVIEW = "needs_review"
    ESCALATE = "escalate"
    INSUFFICIENT_DATA = "insufficient_data"


class ReviewTrigger(str, Enum):
    """Reasons a decision requires human review."""
    LOW_CONFIDENCE = "low_confidence"
    BIAS_DETECTED = "bias_detected"
    PROXY_DETECTED = "proxy_detected"
    CONSENSUS_DISAGREEMENT = "consensus_disagreement"
    HIGH_STAKES_DECISION = "high_stakes_decision"
    REASONING_DIVERGENCE = "reasoning_divergence"
    POLICY_VIOLATION = "policy_violation"
    ADVERSARIAL_CHALLENGE_SUCCEEDED = "adversarial_challenge_succeeded"
    ANALYZER_FAILED = "analyzer_failed"
    STRATEGY_ERROR = "strategy_error"


@dataclass
class StrategyResult:
    """
    Output from an evaluation strategy.

    Contains the decision, confidence, reasoning, and strategy-specific
    details like model votes, criteria scores, or challenge results.

    Attributes:
        strategy_name: Name of the strategy that produced this result
        decision: The outcome (approved, denied, needs_review, etc.)
        confidence: Confidence score from 0.0 to 1.0
        reasoning: Human-readable explanation of the decision

        # Multi-model consensus fields
        model_decisions: Individual decisions from each model
        agreement_level: How much models agreed (0.0 to 1.0)
        dissenting_views: Reasoning from models that disagreed

        # Criteria decomposition fields
        criteria_scores: Scores for individual evaluation criteria

        # Adversarial review fields
        challenges: Challenges raised and their outcomes
        challenge_survived: Whether the decision survived challenges

        # Metadata
        timestamp: When this result was generated
        latency_ms: Total processing time in milliseconds
        tokens_used: Total tokens consumed across all calls
        raw_responses: Raw responses from LLM providers (for debugging)
    """

    strategy_name: str
    decision: DecisionOutcome
    confidence: float  # 0.0 - 1.0
    reasoning: str

    # For multi-model strategies
    model_decisions: List[Dict[str, Any]] = field(default_factory=list)
    agreement_level: Optional[float] = None
    dissenting_views: List[str] = field(default_factory=list)

    # For criteria decomposition
    criteria_scores: Dict[str, Any] = field(default_factory=dict)

    # For adversarial review
    challenges: List[Dict[str, Any]] = field(default_factory=list)
    challenge_survived: bool = True

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    latency_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    raw_responses: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "strategy_name": self.strategy_name,
            "decision": self.decision.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "model_decisions": self.model_decisions,
            "agreement_level": self.agreement_level,
            "dissenting_views": self.dissenting_views,
            "criteria_scores": self.criteria_scores,
            "challenges": self.challenges,
            "challenge_survived": self.challenge_survived,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
        }


@dataclass
class AnalysisResult:
    """
    Output from an analyzer module.

    Contains findings from examining a strategy result for issues
    like bias, logical errors, missing criteria, etc.

    Attributes:
        analyzer_name: Name of the analyzer that produced this result
        passed: Whether the analysis passed (no blocking issues found)

        flags: Critical issues that require attention
        warnings: Concerns that don't block but should be noted

        details: Additional analysis details (analyzer-specific)
        recommendation: Suggested action based on findings

        # Bias detection fields
        detected_attributes: Protected attributes found in reasoning
        detected_proxies: Proxy variables that may indicate bias

        # Gap analysis fields
        matched_criteria: Criteria that were properly addressed
        missing_criteria: Criteria not addressed in reasoning
        partial_criteria: Criteria only partially addressed
    """

    analyzer_name: str
    passed: bool  # Did it pass this analysis?

    flags: List[str] = field(default_factory=list)  # Critical issues
    warnings: List[str] = field(default_factory=list)  # Non-blocking concerns

    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: Optional[str] = None

    # For bias detection
    detected_attributes: List[str] = field(default_factory=list)
    detected_proxies: List[str] = field(default_factory=list)

    # For gap analysis
    matched_criteria: List[str] = field(default_factory=list)
    missing_criteria: List[str] = field(default_factory=list)
    partial_criteria: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "analyzer_name": self.analyzer_name,
            "passed": self.passed,
            "flags": self.flags,
            "warnings": self.warnings,
            "details": self.details,
            "recommendation": self.recommendation,
            "detected_attributes": self.detected_attributes,
            "detected_proxies": self.detected_proxies,
            "matched_criteria": self.matched_criteria,
            "missing_criteria": self.missing_criteria,
            "partial_criteria": self.partial_criteria,
        }


@dataclass
class AccountabilityResult:
    """
    Complete output from TrustChain.

    This is the unified result object that combines strategy output,
    analysis results, and formatted outputs. It's the primary return
    type from TrustChain.evaluate().

    Attributes:
        # Identification
        result_id: Unique identifier for this result
        case_id: External case/application identifier
        decision_type: Type of decision (hiring, benefits, lending, etc.)

        # Core decision
        final_decision: The final outcome after all processing
        overall_confidence: Aggregated confidence score
        requires_human_review: Whether human review is required
        review_triggers: Reasons for requiring review

        # Component outputs
        strategy_result: Output from the evaluation strategy
        analysis_results: Outputs from all analyzer modules

        # Explainability
        primary_reasoning: Main explanation for the decision
        supporting_factors: Evidence supporting the decision
        concerns: Issues or concerns raised during evaluation

        # Consumer explanation
        consumer_summary: Plain-language summary for applicants
        feedback_points: Specific feedback for improvement

        # Audit trail
        input_data_hash: SHA-256 hash of input for integrity
        audit_hash: SHA-256 hash of entire result for tamper detection
        timestamp: When this result was finalized

        # Configuration
        config_snapshot: Copy of configuration used for this evaluation
    """

    # Identification
    result_id: str
    case_id: str
    decision_type: str

    # Core decision
    final_decision: DecisionOutcome
    overall_confidence: float
    requires_human_review: bool
    review_triggers: List[ReviewTrigger] = field(default_factory=list)

    # Component outputs
    strategy_result: Optional[StrategyResult] = None
    analysis_results: List[AnalysisResult] = field(default_factory=list)

    # Explainability
    primary_reasoning: str = ""
    supporting_factors: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)

    # For consumer explanation
    consumer_summary: Optional[str] = None
    feedback_points: List[Dict[str, Any]] = field(default_factory=list)

    # Audit trail
    input_data_hash: str = ""  # Hash of input for integrity
    audit_hash: str = ""  # Hash of entire result
    timestamp: datetime = field(default_factory=datetime.now)

    # Configuration used
    config_snapshot: Dict[str, Any] = field(default_factory=dict)

    def calculate_audit_hash(self) -> str:
        """
        Generate tamper-evident hash of the result.

        Creates a deterministic SHA-256 hash of key result fields
        that can be used to verify the result hasn't been modified.

        Returns:
            Hexadecimal SHA-256 hash string
        """
        hash_content = {
            "result_id": self.result_id,
            "case_id": self.case_id,
            "decision_type": self.decision_type,
            "final_decision": self.final_decision.value,
            "confidence": self.overall_confidence,
            "requires_human_review": self.requires_human_review,
            "timestamp": self.timestamp.isoformat(),
            "reasoning": self.primary_reasoning,
            "input_data_hash": self.input_data_hash,
        }
        return hashlib.sha256(
            json.dumps(hash_content, sort_keys=True).encode()
        ).hexdigest()

    def calculate_input_hash(self, input_data: Dict[str, Any]) -> str:
        """
        Generate hash of input data for integrity verification.

        Args:
            input_data: The original input data to hash

        Returns:
            Hexadecimal SHA-256 hash string
        """
        return hashlib.sha256(
            json.dumps(input_data, sort_keys=True, default=str).encode()
        ).hexdigest()

    def finalize(self, input_data: Optional[Dict[str, Any]] = None) -> "AccountabilityResult":
        """
        Lock the result and generate audit hashes.

        Call this after all processing is complete to generate
        tamper-evident hashes. Once finalized, the audit_hash
        can be used to verify the result hasn't been modified.

        Args:
            input_data: Optional input data to hash for integrity

        Returns:
            Self with audit hashes populated
        """
        if input_data:
            self.input_data_hash = self.calculate_input_hash(input_data)
        self.audit_hash = self.calculate_audit_hash()
        return self

    def verify_integrity(self) -> bool:
        """
        Verify the result hasn't been tampered with.

        Recalculates the audit hash and compares it to the stored hash.

        Returns:
            True if the result is intact, False if modified
        """
        return self.audit_hash == self.calculate_audit_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "result_id": self.result_id,
            "case_id": self.case_id,
            "decision_type": self.decision_type,
            "final_decision": self.final_decision.value,
            "overall_confidence": self.overall_confidence,
            "requires_human_review": self.requires_human_review,
            "review_triggers": [t.value for t in self.review_triggers],
            "strategy_result": self.strategy_result.to_dict() if self.strategy_result else None,
            "analysis_results": [ar.to_dict() for ar in self.analysis_results],
            "primary_reasoning": self.primary_reasoning,
            "supporting_factors": self.supporting_factors,
            "concerns": self.concerns,
            "consumer_summary": self.consumer_summary,
            "feedback_points": self.feedback_points,
            "input_data_hash": self.input_data_hash,
            "audit_hash": self.audit_hash,
            "timestamp": self.timestamp.isoformat(),
            "config_snapshot": self.config_snapshot,
        }

    def to_foia_report(self) -> Dict[str, Any]:
        """
        Generate FOIA-compliant report.

        Returns a version of the result suitable for Freedom of Information
        Act requests, with sensitive internal details redacted.

        Returns:
            Dictionary with FOIA-safe information
        """
        return {
            "result_id": self.result_id,
            "case_id": self.case_id,
            "decision_type": self.decision_type,
            "final_decision": self.final_decision.value,
            "requires_human_review": self.requires_human_review,
            "primary_reasoning": self.primary_reasoning,
            "supporting_factors": self.supporting_factors,
            "concerns": self.concerns,
            "consumer_summary": self.consumer_summary,
            "feedback_points": self.feedback_points,
            "timestamp": self.timestamp.isoformat(),
            "audit_hash": self.audit_hash,
            # Exclude: raw_responses, config_snapshot, internal details
        }

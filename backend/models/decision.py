"""
Decision models for TrustChain.

Defines the data structures for government decisions, consensus outcomes,
and FOIA-compliant audit trails.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import hashlib
import json


class DecisionStatus(str, Enum):
    """Status of a decision in the system."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class DecisionOutcome(str, Enum):
    """Final outcome of a decision."""
    APPROVED = "approved"
    DENIED = "denied"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    INSUFFICIENT_DATA = "insufficient_data"


class ModelDecision(BaseModel):
    """
    Decision from a single AI model.

    Represents one model's analysis of a case, including its reasoning
    and confidence level. Multiple ModelDecisions combine to form consensus.
    """
    model_provider: str = Field(..., description="Provider name (anthropic, openai, llama)")
    model_name: str = Field(..., description="Specific model version used")
    decision: DecisionOutcome = Field(..., description="The model's decision")
    reasoning: str = Field(..., description="Step-by-step reasoning process")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    latency_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "model_provider": "anthropic",
                "model_name": "claude-3-opus-20240229",
                "decision": "approved",
                "reasoning": "Applicant meets all eligibility criteria...",
                "confidence": 0.85,
                "timestamp": "2025-01-15T10:30:00Z",
                "tokens_used": 1250,
                "latency_ms": 2340.5
            }
        }


class ConsensusAnalysis(BaseModel):
    """
    Analysis of consensus among multiple model decisions.

    Critical for identifying disagreements that require human review
    and ensuring diverse AI perspectives are considered.
    """
    agreement_level: float = Field(..., ge=0.0, le=1.0, description="0=total disagreement, 1=full consensus")
    majority_decision: DecisionOutcome = Field(..., description="Decision supported by most models")
    dissenting_models: List[str] = Field(default_factory=list, description="Models that disagreed")
    confidence_variance: float = Field(..., description="Variance in confidence scores")
    reasoning_divergence: Optional[str] = Field(None, description="Analysis of reasoning differences")

    @validator('agreement_level')
    def validate_agreement(cls, v):
        """Ensure agreement level is in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Agreement level must be between 0 and 1")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "agreement_level": 0.85,
                "majority_decision": "approved",
                "dissenting_models": [],
                "confidence_variance": 0.05,
                "reasoning_divergence": None
            }
        }


class BiasDetection(BaseModel):
    """
    Bias detection analysis for government compliance.

    Identifies potential bias in decision-making process to ensure
    fairness and equal treatment under government regulations.
    """
    bias_detected: bool = Field(..., description="Whether potential bias was found")
    bias_type: Optional[str] = Field(None, description="Type of bias if detected")
    affected_attributes: List[str] = Field(default_factory=list, description="Attributes that may show bias")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in bias detection")
    recommendation: Optional[str] = Field(None, description="Recommended action")

    class Config:
        json_schema_extra = {
            "example": {
                "bias_detected": False,
                "bias_type": None,
                "affected_attributes": [],
                "confidence": 0.92,
                "recommendation": None
            }
        }


class Decision(BaseModel):
    """
    Complete decision record for TrustChain.

    Represents a full government decision with multi-model consensus,
    audit trail, and FOIA compliance metadata.
    """
    decision_id: str = Field(..., description="Unique decision identifier")
    case_id: str = Field(..., description="Government case/application ID")
    decision_type: str = Field(..., description="Type of decision (e.g., 'unemployment_benefits')")
    applicant_id: Optional[str] = Field(None, description="Anonymized applicant identifier")

    # Input data
    input_data: Dict[str, Any] = Field(..., description="Decision input parameters")
    policy_context: str = Field(..., description="Government policy and legal framework")

    # Model decisions
    model_decisions: List[ModelDecision] = Field(default_factory=list, description="Individual model decisions")

    # Consensus outcome
    final_decision: Optional[DecisionOutcome] = Field(None, description="Final consensus decision")
    consensus_analysis: Optional[ConsensusAnalysis] = Field(None, description="Consensus analysis")

    # Bias detection
    bias_analysis: Optional[BiasDetection] = Field(None, description="Bias detection results")

    # Status and metadata
    status: DecisionStatus = Field(default=DecisionStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None)
    reviewed_by_human: bool = Field(default=False, description="Whether a human reviewed this decision")
    human_reviewer_id: Optional[str] = Field(None)

    # FOIA compliance
    foia_compliant: bool = Field(default=True, description="Whether decision meets FOIA requirements")
    audit_hash: Optional[str] = Field(None, description="Cryptographic hash for audit trail")

    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "dec_2025_001234",
                "case_id": "unemp_app_987654",
                "decision_type": "unemployment_benefits",
                "input_data": {
                    "employment_duration": 18,
                    "termination_reason": "layoff",
                    "earnings": 45000
                },
                "policy_context": "State unemployment eligibility requirements...",
                "status": "completed",
                "final_decision": "approved"
            }
        }

    def calculate_audit_hash(self) -> str:
        """
        Calculate cryptographic hash for immutable audit trail.

        Creates a SHA-256 hash of critical decision data to ensure
        the decision record cannot be altered without detection.

        Returns:
            Hexadecimal hash string
        """
        # Build canonical representation of decision data
        audit_data = {
            "decision_id": self.decision_id,
            "case_id": self.case_id,
            "input_data": self.input_data,
            "model_decisions": [
                {
                    "provider": md.model_provider,
                    "decision": md.decision.value,
                    "reasoning": md.reasoning,
                    "confidence": md.confidence
                }
                for md in self.model_decisions
            ],
            "final_decision": self.final_decision.value if self.final_decision else None,
            "timestamp": self.created_at.isoformat()
        }

        # Create deterministic JSON string
        canonical_json = json.dumps(audit_data, sort_keys=True)

        # Calculate SHA-256 hash
        hash_obj = hashlib.sha256(canonical_json.encode())
        return hash_obj.hexdigest()

    def verify_audit_hash(self) -> bool:
        """
        Verify that the stored audit hash matches current data.

        Returns:
            True if hash is valid, False if data has been tampered with
        """
        if not self.audit_hash:
            return False

        calculated_hash = self.calculate_audit_hash()
        return calculated_hash == self.audit_hash

    def to_foia_report(self) -> Dict[str, Any]:
        """
        Convert decision to FOIA-compliant report format.

        Removes sensitive personal information while preserving
        decision-making transparency for public records requests.

        Returns:
            FOIA-compliant dictionary
        """
        return {
            "decision_id": self.decision_id,
            "case_id": self.case_id,
            "decision_type": self.decision_type,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "final_decision": self.final_decision.value if self.final_decision else None,
            "model_count": len(self.model_decisions),
            "consensus_level": self.consensus_analysis.agreement_level if self.consensus_analysis else None,
            "bias_detected": self.bias_analysis.bias_detected if self.bias_analysis else None,
            "human_reviewed": self.reviewed_by_human,
            "audit_hash": self.audit_hash
        }


class DecisionRequest(BaseModel):
    """
    Request model for initiating a new decision.

    Used by API clients to submit cases for AI decision-making.
    """
    case_id: str = Field(..., description="Government case/application ID")
    decision_type: str = Field(..., description="Type of decision being requested")
    input_data: Dict[str, Any] = Field(..., description="Case details and parameters")
    policy_context: str = Field(..., description="Relevant policy and legal framework")
    require_consensus: bool = Field(default=True, description="Whether to require model consensus")
    applicant_id: Optional[str] = Field(None, description="Anonymized applicant ID")

    class Config:
        json_schema_extra = {
            "example": {
                "case_id": "unemp_app_987654",
                "decision_type": "unemployment_benefits",
                "input_data": {
                    "employment_duration_months": 18,
                    "termination_reason": "layoff",
                    "prior_earnings": 45000,
                    "available_for_work": True
                },
                "policy_context": "State unemployment insurance eligibility requirements...",
                "require_consensus": True
            }
        }


class DecisionResponse(BaseModel):
    """
    Response model for decision API endpoints.

    Provides the decision result with full transparency data.
    """
    decision_id: str
    status: DecisionStatus
    final_decision: Optional[DecisionOutcome]
    consensus_analysis: Optional[ConsensusAnalysis]
    model_decisions: List[ModelDecision]
    requires_human_review: bool
    audit_hash: str

    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "dec_2025_001234",
                "status": "completed",
                "final_decision": "approved",
                "consensus_analysis": {
                    "agreement_level": 0.95,
                    "majority_decision": "approved"
                },
                "model_decisions": [],
                "requires_human_review": False,
                "audit_hash": "a1b2c3d4e5f6..."
            }
        }

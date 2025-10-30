"""
Bias Detection and Safety Service for TrustChain.

This module implements critical safeguards for high-stakes government decisions
like unemployment benefits, immigration, healthcare, etc.

CRITICAL: This system can affect people's lives. Every line of code here
          prioritizes safety, fairness, and accountability.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set
from enum import Enum

from models import BiasDetection

logger = logging.getLogger(__name__)


class ProtectedAttribute(str, Enum):
    """
    Protected attributes under civil rights law.

    These attributes should NEVER be the basis for government decisions.
    If detected in reasoning, flag immediately for human review.
    """
    RACE = "race"
    ETHNICITY = "ethnicity"
    NATIONAL_ORIGIN = "national_origin"
    GENDER = "gender"
    AGE = "age"
    RELIGION = "religion"
    DISABILITY = "disability"
    SEXUAL_ORIENTATION = "sexual_orientation"
    PREGNANCY = "pregnancy"
    VETERAN_STATUS = "veteran_status"


class SafetyTrigger(str, Enum):
    """
    Conditions that REQUIRE human review regardless of consensus.

    These are hard stops - the system will NOT auto-approve/deny.
    """
    PROTECTED_ATTRIBUTE_MENTIONED = "protected_attribute_mentioned"
    LOW_CONFIDENCE_CONSENSUS = "low_confidence_consensus"
    HIGH_STAKES_DECISION = "high_stakes_decision"
    CONFLICTING_REASONING = "conflicting_reasoning"
    INSUFFICIENT_DATA = "insufficient_data"
    DEPORTATION_RISK = "deportation_risk"
    BENEFIT_TERMINATION = "benefit_termination"


class BiasDetectionService:
    """
    Detects potential bias and enforces safety requirements.

    This is the "guardian" of the system - it looks for red flags
    that humans MUST review before any decision is finalized.
    """

    # Keywords that indicate protected attributes being discussed
    PROTECTED_KEYWORDS = {
        ProtectedAttribute.RACE: [
            "race", "racial", "black", "white", "asian", "hispanic",
            "latino", "latina", "african american", "caucasian"
        ],
        ProtectedAttribute.ETHNICITY: [
            "ethnicity", "ethnic", "minority", "cultural background"
        ],
        ProtectedAttribute.NATIONAL_ORIGIN: [
            "country of origin", "nationality", "immigrant", "foreign",
            "native-born", "birthplace", "citizen", "citizenship"
        ],
        ProtectedAttribute.GENDER: [
            "gender", "male", "female", "man", "woman", "sex",
            "transgender", "non-binary"
        ],
        ProtectedAttribute.AGE: [
            "age", "elderly", "senior", "young", "older worker",
            "retirement age", "generational"
        ],
        ProtectedAttribute.RELIGION: [
            "religion", "religious", "christian", "muslim", "jewish",
            "hindu", "buddhist", "atheist", "faith"
        ],
        ProtectedAttribute.DISABILITY: [
            "disability", "disabled", "handicap", "impairment",
            "medical condition", "accommodation"
        ],
        ProtectedAttribute.SEXUAL_ORIENTATION: [
            "sexual orientation", "gay", "lesbian", "bisexual",
            "lgbtq", "homosexual", "heterosexual"
        ],
        ProtectedAttribute.PREGNANCY: [
            "pregnancy", "pregnant", "maternity", "childbirth",
            "expecting", "parental leave"
        ],
        ProtectedAttribute.VETERAN_STATUS: [
            "veteran", "military service", "armed forces", "discharge"
        ]
    }

    def __init__(
        self,
        strict_mode: bool = True,
        confidence_threshold: float = 0.7
    ):
        """
        Initialize bias detection service.

        Args:
            strict_mode: If True, flag ANY mention of protected attributes
            confidence_threshold: Minimum confidence to auto-decide (0.7 = 70%)
        """
        self.strict_mode = strict_mode
        self.confidence_threshold = confidence_threshold

        logger.info(
            f"Bias detection initialized - Strict mode: {strict_mode}, "
            f"Confidence threshold: {confidence_threshold:.0%}"
        )

    def analyze_decision(
        self,
        model_decisions: List[Any],
        consensus_analysis: Any,
        decision_type: str,
        input_data: Dict[str, Any]
    ) -> BiasDetection:
        """
        Comprehensive bias and safety analysis.

        This is the MAIN safety check - runs multiple analyses:
        1. Scan for protected attributes in reasoning
        2. Check confidence levels
        3. Identify high-stakes decisions
        4. Detect conflicting reasoning
        5. Determine if human review is mandatory

        Args:
            model_decisions: List of decisions from AI models
            consensus_analysis: Consensus analysis object
            decision_type: Type of decision (e.g., "immigration_deportation")
            input_data: Raw application data

        Returns:
            BiasDetection object with safety recommendations
        """
        logger.info(f"🔍 Running bias detection for {decision_type}...")

        detected_attributes: Set[str] = set()
        safety_triggers: List[SafetyTrigger] = []

        # CHECK 1: Scan reasoning for protected attributes
        logger.debug("Checking for protected attribute mentions...")
        for model_decision in model_decisions:
            reasoning = model_decision.reasoning.lower()

            for attr, keywords in self.PROTECTED_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in reasoning:
                        detected_attributes.add(attr.value)
                        safety_triggers.append(
                            SafetyTrigger.PROTECTED_ATTRIBUTE_MENTIONED
                        )
                        logger.warning(
                            f"⚠️  Protected attribute detected: {attr.value} "
                            f"(keyword: '{keyword}') in {model_decision.model_provider}"
                        )

        # CHECK 2: Low confidence consensus
        logger.debug("Checking confidence levels...")
        confidences = [md.confidence for md in model_decisions]
        avg_confidence = sum(confidences) / len(confidences)

        if avg_confidence < self.confidence_threshold:
            safety_triggers.append(SafetyTrigger.LOW_CONFIDENCE_CONSENSUS)
            logger.warning(
                f"⚠️  Low confidence: {avg_confidence:.0%} < {self.confidence_threshold:.0%}"
            )

        # CHECK 3: High-stakes decision types
        high_stakes_types = [
            "immigration_deportation",
            "asylum_decision",
            "benefit_termination",
            "housing_denial",
            "loan_denial",
            "employment_termination"
        ]

        if decision_type in high_stakes_types:
            safety_triggers.append(SafetyTrigger.HIGH_STAKES_DECISION)
            logger.warning(f"⚠️  High-stakes decision type: {decision_type}")

        # CHECK 4: Conflicting reasoning (models agree on decision but for different reasons)
        if consensus_analysis.agreement_level == 1.0:  # All agree on decision
            # But check if reasoning varies significantly
            if consensus_analysis.confidence_variance > 0.1:
                safety_triggers.append(SafetyTrigger.CONFLICTING_REASONING)
                logger.warning(
                    f"⚠️  High confidence variance despite consensus: "
                    f"{consensus_analysis.confidence_variance:.4f}"
                )

        # CHECK 5: Insufficient data
        required_fields = self._get_required_fields(decision_type)
        missing_fields = [f for f in required_fields if f not in input_data]

        if missing_fields:
            safety_triggers.append(SafetyTrigger.INSUFFICIENT_DATA)
            logger.warning(f"⚠️  Missing required fields: {missing_fields}")

        # CHECK 6: Deportation risk (CRITICAL)
        if decision_type in ["immigration_deportation", "visa_denial"]:
            safety_triggers.append(SafetyTrigger.DEPORTATION_RISK)
            logger.critical(
                "🚨 DEPORTATION RISK - Mandatory human review required"
            )

        # Determine if bias was detected
        bias_detected = len(detected_attributes) > 0 or len(safety_triggers) > 0

        # Generate recommendation
        recommendation = self._generate_recommendation(
            bias_detected,
            detected_attributes,
            safety_triggers,
            avg_confidence
        )

        bias_analysis = BiasDetection(
            bias_detected=bias_detected,
            bias_type=self._categorize_bias(detected_attributes, safety_triggers),
            affected_attributes=list(detected_attributes),
            confidence=1.0 - avg_confidence if bias_detected else avg_confidence,
            recommendation=recommendation
        )

        if bias_detected:
            logger.warning(
                f"⚠️  Bias detection result: {len(detected_attributes)} protected "
                f"attributes, {len(safety_triggers)} safety triggers"
            )
        else:
            logger.info("✓ No bias indicators detected")

        return bias_analysis

    def requires_mandatory_review(
        self,
        bias_analysis: BiasDetection,
        decision_type: str,
        consensus_level: float
    ) -> bool:
        """
        Determine if human review is MANDATORY (not optional).

        Some decisions are too important to automate completely.
        This enforces human-in-the-loop for critical cases.

        Args:
            bias_analysis: Bias detection results
            decision_type: Type of decision
            consensus_level: Agreement level among models

        Returns:
            True if human MUST review before finalizing
        """
        # RULE 1: ANY protected attribute mention = mandatory review
        if bias_analysis.affected_attributes:
            logger.critical(
                f"🚨 MANDATORY REVIEW: Protected attributes detected - "
                f"{bias_analysis.affected_attributes}"
            )
            return True

        # RULE 2: Deportation or life-altering decisions = ALWAYS review
        critical_types = [
            "immigration_deportation",
            "asylum_decision",
            "benefit_termination"
        ]
        if decision_type in critical_types:
            logger.critical(
                f"🚨 MANDATORY REVIEW: Critical decision type - {decision_type}"
            )
            return True

        # RULE 3: Low consensus + bias detected = mandatory review
        if consensus_level < 0.66 and bias_analysis.bias_detected:
            logger.critical(
                f"🚨 MANDATORY REVIEW: Low consensus ({consensus_level:.0%}) "
                f"+ bias indicators"
            )
            return True

        # RULE 4: Very low consensus (< 50%) = always review
        if consensus_level < 0.5:
            logger.critical(
                f"🚨 MANDATORY REVIEW: Very low consensus ({consensus_level:.0%})"
            )
            return True

        return False

    def _get_required_fields(self, decision_type: str) -> List[str]:
        """
        Get required fields for each decision type.

        Missing required fields = insufficient data = flag for review.
        """
        field_requirements = {
            "unemployment_benefits": [
                "employment_duration_months",
                "termination_reason",
                "available_for_work"
            ],
            "immigration_deportation": [
                "visa_status",
                "entry_date",
                "criminal_record",
                "family_ties"
            ],
            "loan_approval": [
                "credit_score",
                "income",
                "debt_to_income_ratio"
            ]
        }

        return field_requirements.get(decision_type, [])

    def _categorize_bias(
        self,
        detected_attributes: Set[str],
        safety_triggers: List[SafetyTrigger]
    ) -> Optional[str]:
        """Categorize the type of bias detected."""
        if not detected_attributes and not safety_triggers:
            return None

        if detected_attributes:
            return f"protected_attribute_bias ({', '.join(detected_attributes)})"

        if SafetyTrigger.LOW_CONFIDENCE_CONSENSUS in safety_triggers:
            return "confidence_bias"

        if SafetyTrigger.CONFLICTING_REASONING in safety_triggers:
            return "reasoning_inconsistency"

        return "safety_concern"

    def _generate_recommendation(
        self,
        bias_detected: bool,
        detected_attributes: Set[str],
        safety_triggers: List[SafetyTrigger],
        avg_confidence: float
    ) -> str:
        """Generate human-readable safety recommendation."""
        if not bias_detected:
            return "No bias indicators detected. Decision may proceed if consensus is adequate."

        recommendations = []

        if detected_attributes:
            recommendations.append(
                f"CRITICAL: Protected attributes mentioned ({', '.join(detected_attributes)}). "
                f"Verify decision is not based on discriminatory factors."
            )

        if SafetyTrigger.LOW_CONFIDENCE_CONSENSUS in safety_triggers:
            recommendations.append(
                f"Models show low confidence ({avg_confidence:.0%}). "
                f"Review case for missing information or ambiguity."
            )

        if SafetyTrigger.HIGH_STAKES_DECISION in safety_triggers:
            recommendations.append(
                "High-stakes decision with significant impact on applicant. "
                "Ensure thorough review of all factors."
            )

        if SafetyTrigger.DEPORTATION_RISK in safety_triggers:
            recommendations.append(
                "DEPORTATION RISK: This decision could result in removal from country. "
                "Mandatory legal review and applicant notification required."
            )

        return " ".join(recommendations)


# Singleton instance for global access
_bias_detector = None


def get_bias_detector(
    strict_mode: bool = True,
    confidence_threshold: float = 0.7
) -> BiasDetectionService:
    """
    Get the global bias detection service instance.

    Args:
        strict_mode: Enable strict bias detection
        confidence_threshold: Minimum confidence for auto-decisions

    Returns:
        BiasDetectionService instance
    """
    global _bias_detector

    if _bias_detector is None:
        _bias_detector = BiasDetectionService(
            strict_mode=strict_mode,
            confidence_threshold=confidence_threshold
        )

    return _bias_detector

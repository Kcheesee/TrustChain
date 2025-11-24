"""
Consumer Explanation Output Generator for TrustChain.

Generates plain-language explanations suitable for applicants and
end users. Unlike internal audit reports, these are:

- Written in simple, accessible language
- Free of technical jargon
- Focused on actionable feedback
- Compliant with explainability requirements

This is crucial for:
- GDPR Article 22 (right to explanation)
- ECOA adverse action notices
- Building trust with users
- Reducing appeals and complaints

Built with care by Kareem & Claude
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.base import BaseOutput
from core.registry import register_component
from core.result import AccountabilityResult, DecisionOutcome

logger = logging.getLogger(__name__)


@register_component
class ConsumerExplanationOutput(BaseOutput):
    """
    Consumer explanation output generator.

    Creates plain-language explanations suitable for applicants,
    including decision summary, key factors, and actionable feedback.

    Configuration options:
        language_level: 'simple', 'standard', 'formal' (default: simple)
        include_appeal_info: Include appeal process info (default: True)
        include_feedback: Include improvement suggestions (default: True)
        max_factors: Maximum factors to list (default: 5)
        redact_model_names: Hide AI model names (default: True)

    Example:
        output = ConsumerExplanationOutput(config={
            "language_level": "simple",
            "include_appeal_info": True
        })
    """

    name = "consumer_explanation"
    description = "Generate plain-language explanations for applicants"
    version = "1.0.0"
    output_format = "json"

    # Templates for different decision outcomes
    DECISION_TEMPLATES = {
        DecisionOutcome.APPROVED: {
            "simple": "Good news! Your {decision_type} application has been approved.",
            "standard": "We are pleased to inform you that your {decision_type} application has been approved.",
            "formal": "This letter confirms the approval of your {decision_type} application.",
        },
        DecisionOutcome.DENIED: {
            "simple": "We're sorry, but your {decision_type} application was not approved at this time.",
            "standard": "After careful review, we were unable to approve your {decision_type} application.",
            "formal": "Following a thorough evaluation, we regret to inform you that your {decision_type} application has not been approved.",
        },
        DecisionOutcome.NEEDS_REVIEW: {
            "simple": "Your {decision_type} application needs additional review before a decision can be made.",
            "standard": "Your {decision_type} application requires further review by our team.",
            "formal": "Your {decision_type} application has been flagged for additional human review.",
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize consumer explanation output generator."""
        super().__init__(config)

        self.language_level = self.config.get("language_level", "simple")
        self.include_appeal_info = self.config.get("include_appeal_info", True)
        self.include_feedback = self.config.get("include_feedback", True)
        self.max_factors = self.config.get("max_factors", 5)
        self.redact_model_names = self.config.get("redact_model_names", True)

        logger.info(
            f"ConsumerExplanationOutput initialized: "
            f"language={self.language_level}, "
            f"appeal_info={self.include_appeal_info}"
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate output configuration."""
        valid_levels = ["simple", "standard", "formal"]
        if "language_level" in config and config["language_level"] not in valid_levels:
            raise ValueError(f"language_level must be one of: {valid_levels}")
        return True

    def generate(self, accountability_result: AccountabilityResult) -> Dict[str, Any]:
        """
        Generate consumer explanation.

        Args:
            accountability_result: Complete TrustChain result

        Returns:
            Dictionary with consumer-friendly explanation
        """
        logger.info("Generating consumer explanation...")

        result = accountability_result

        # Generate main summary
        summary = self._generate_summary(result)

        # Extract key factors
        key_factors = self._extract_key_factors(result)

        # Generate feedback/improvement suggestions
        feedback = self._generate_feedback(result) if self.include_feedback else []

        # Generate appeal information
        appeal_info = self._generate_appeal_info(result) if self.include_appeal_info else None

        # Build the explanation
        explanation = {
            "generated_at": datetime.now().isoformat(),
            "case_id": result.case_id,
            "decision_type": self._humanize_decision_type(result.decision_type),
            "decision": result.final_decision.value,
            "summary": summary,
            "key_factors": key_factors,
            "confidence_statement": self._generate_confidence_statement(result),
            "requires_human_review": result.requires_human_review,
        }

        if feedback:
            explanation["feedback"] = feedback

        if appeal_info:
            explanation["appeal_information"] = appeal_info

        if result.requires_human_review:
            explanation["review_notice"] = self._generate_review_notice(result)

        logger.info(f"Generated consumer explanation for {result.case_id}")

        return explanation

    def _generate_summary(self, result: AccountabilityResult) -> str:
        """Generate the main decision summary."""
        decision = result.final_decision
        decision_type = self._humanize_decision_type(result.decision_type)

        # Get template based on decision and language level
        templates = self.DECISION_TEMPLATES.get(
            decision,
            self.DECISION_TEMPLATES[DecisionOutcome.NEEDS_REVIEW]
        )
        template = templates.get(self.language_level, templates["simple"])

        summary = template.format(decision_type=decision_type)

        # Add brief reasoning
        if result.primary_reasoning and self.language_level != "simple":
            summary += f" {self._simplify_reasoning(result.primary_reasoning)}"

        return summary

    def _extract_key_factors(self, result: AccountabilityResult) -> List[Dict[str, Any]]:
        """Extract key factors that influenced the decision."""
        factors = []

        # From supporting factors
        for factor in result.supporting_factors[:self.max_factors]:
            factors.append({
                "factor": self._simplify_text(factor),
                "impact": "positive" if result.final_decision == DecisionOutcome.APPROVED else "considered",
            })

        # From concerns
        for concern in result.concerns[:self.max_factors - len(factors)]:
            factors.append({
                "factor": self._simplify_text(concern),
                "impact": "concern",
            })

        # From criteria scores if available
        if result.strategy_result and result.strategy_result.criteria_scores:
            for crit_name, crit_data in list(result.strategy_result.criteria_scores.items())[:self.max_factors]:
                if isinstance(crit_data, dict):
                    passed = crit_data.get("passed", False)
                    score = crit_data.get("score", 0)

                    factor_text = self._humanize_criterion(crit_name)
                    if passed:
                        factors.append({
                            "factor": f"Met requirement: {factor_text}",
                            "impact": "positive",
                        })
                    else:
                        factors.append({
                            "factor": f"Did not fully meet: {factor_text}",
                            "impact": "area_for_improvement",
                            "details": f"Score: {score:.0%}" if score else None,
                        })

        return factors[:self.max_factors]

    def _generate_feedback(self, result: AccountabilityResult) -> List[Dict[str, Any]]:
        """Generate actionable feedback for the applicant."""
        feedback = []

        decision = result.final_decision

        if decision == DecisionOutcome.APPROVED:
            feedback.append({
                "type": "info",
                "message": "Your application met all requirements. No further action needed.",
            })

        elif decision == DecisionOutcome.DENIED:
            # Generate improvement suggestions based on concerns
            for concern in result.concerns[:3]:
                suggestion = self._concern_to_suggestion(concern)
                if suggestion:
                    feedback.append({
                        "type": "improvement",
                        "message": suggestion,
                    })

            if not feedback:
                feedback.append({
                    "type": "info",
                    "message": "Please review the key factors above for areas that may need attention.",
                })

        elif decision == DecisionOutcome.NEEDS_REVIEW:
            feedback.append({
                "type": "info",
                "message": "Your application is being reviewed. A human reviewer will examine your case and may contact you for additional information.",
            })

        # Add feedback from analysis results
        for analysis in result.analysis_results:
            if analysis.recommendation and not analysis.passed:
                feedback.append({
                    "type": "notice",
                    "message": self._simplify_text(analysis.recommendation),
                })

        return feedback

    def _generate_appeal_info(self, result: AccountabilityResult) -> Dict[str, Any]:
        """Generate information about the appeal process."""
        decision = result.final_decision

        if decision == DecisionOutcome.APPROVED:
            return None

        appeal_info = {
            "can_appeal": True,
            "deadline": "30 days from this notice",  # Configurable in future
            "process": self._get_appeal_process(result.decision_type),
        }

        if self.language_level == "simple":
            appeal_info["summary"] = (
                "If you believe this decision is wrong, you can ask for a review. "
                "Please do this within 30 days."
            )
        else:
            appeal_info["summary"] = (
                "You have the right to appeal this decision. "
                "Appeals must be submitted within 30 days of this notice."
            )

        return appeal_info

    def _generate_review_notice(self, result: AccountabilityResult) -> str:
        """Generate notice about human review."""
        triggers = result.review_triggers

        if self.language_level == "simple":
            return (
                "A person will look at your application to make sure the decision is fair. "
                "This usually takes 3-5 business days."
            )
        else:
            return (
                "Your application has been flagged for human review to ensure fairness and accuracy. "
                "A trained reviewer will examine your case within 3-5 business days."
            )

    def _generate_confidence_statement(self, result: AccountabilityResult) -> str:
        """Generate a confidence statement."""
        confidence = result.overall_confidence

        if confidence >= 0.9:
            return "This decision was made with high confidence based on the information provided."
        elif confidence >= 0.7:
            return "This decision was made with reasonable confidence based on the available information."
        else:
            return "Due to some uncertainty, this decision will receive additional review."

    def _humanize_decision_type(self, decision_type: str) -> str:
        """Convert decision type to human-readable format."""
        humanized = {
            "unemployment_benefits": "unemployment benefits",
            "hiring": "job application",
            "loan_approval": "loan",
            "immigration_deportation": "immigration",
            "benefit_termination": "benefits continuation",
            "visa_denial": "visa",
        }
        return humanized.get(decision_type, decision_type.replace("_", " "))

    def _humanize_criterion(self, criterion: str) -> str:
        """Convert criterion name to human-readable format."""
        humanized = {
            "employment_duration": "Employment history requirement",
            "termination_reason": "Reason for leaving previous job",
            "availability": "Availability for work",
            "experience": "Work experience",
            "skills": "Required skills",
            "education": "Education requirements",
            "credit_score": "Credit history",
            "income": "Income verification",
            "debt_ratio": "Debt-to-income ratio",
        }
        return humanized.get(criterion, criterion.replace("_", " ").title())

    def _simplify_reasoning(self, reasoning: str) -> str:
        """Simplify technical reasoning for consumers."""
        # Remove technical terms
        simplified = reasoning

        # Limit length
        if len(simplified) > 200:
            simplified = simplified[:200].rsplit(' ', 1)[0] + "..."

        return simplified

    def _simplify_text(self, text: str) -> str:
        """Simplify text for consumer readability."""
        # Remove protected attribute mentions if present
        sensitive_terms = [
            "protected attribute", "bias detected", "proxy variable",
            "confidence variance", "consensus", "strategy result"
        ]

        simplified = text
        for term in sensitive_terms:
            simplified = simplified.replace(term, "additional factor")

        return simplified

    def _concern_to_suggestion(self, concern: str) -> Optional[str]:
        """Convert a concern into an actionable suggestion."""
        concern_lower = concern.lower()

        suggestions = {
            "employment": "Consider documenting your complete employment history.",
            "experience": "You may want to highlight relevant experience in future applications.",
            "income": "Providing additional income documentation may strengthen your application.",
            "credit": "Working on improving your credit score may help with future applications.",
            "documentation": "Ensure all required documents are complete and up to date.",
        }

        for key, suggestion in suggestions.items():
            if key in concern_lower:
                return suggestion

        return None

    def _get_appeal_process(self, decision_type: str) -> List[str]:
        """Get appeal process steps for decision type."""
        base_steps = [
            "Review this explanation and the key factors listed above",
            "Gather any additional documentation that supports your case",
            "Submit your appeal in writing within the deadline",
            "Include your case reference number in all communications",
        ]

        if decision_type in ["unemployment_benefits", "benefit_termination"]:
            base_steps.append("You may also request an in-person hearing")

        return base_steps

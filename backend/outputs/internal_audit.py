"""
Internal Audit Output Generator for TrustChain.

Generates detailed audit logs for compliance teams, including
full decision trails, analysis results, and tamper-evident hashing.

Built with care by Kareem & Claude
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.base import BaseOutput
from core.registry import register_component
from core.result import AccountabilityResult

logger = logging.getLogger(__name__)


@register_component
class InternalAuditOutput(BaseOutput):
    """
    Internal audit output generator.

    Produces comprehensive audit reports suitable for:
    - Internal compliance reviews
    - Regulatory audits
    - Legal discovery
    - Incident investigation

    Configuration options:
        include_raw_responses: Include raw LLM responses (default False)
        include_config_snapshot: Include config used (default True)
        redact_pii: Attempt to redact PII from output (default False)
        format: Output format - 'full', 'summary', 'compliance' (default 'full')

    Example:
        output = InternalAuditOutput(config={
            "include_raw_responses": False,
            "format": "full"
        })
        audit_report = output.generate(accountability_result)
    """

    name = "internal_audit"
    description = "Generate detailed audit logs for compliance teams"
    version = "1.0.0"
    output_format = "json"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the internal audit output generator."""
        super().__init__(config)

        self.include_raw_responses = self.config.get("include_raw_responses", False)
        self.include_config_snapshot = self.config.get("include_config_snapshot", True)
        self.redact_pii = self.config.get("redact_pii", False)
        self.format_type = self.config.get("format", "full")

        logger.info(
            f"InternalAuditOutput initialized: "
            f"format={self.format_type}, "
            f"include_raw={self.include_raw_responses}"
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate output configuration."""
        valid_formats = ["full", "summary", "compliance"]
        if "format" in config and config["format"] not in valid_formats:
            raise ValueError(f"format must be one of: {valid_formats}")
        return True

    def generate(self, accountability_result: AccountabilityResult) -> Dict[str, Any]:
        """
        Generate internal audit report.

        Args:
            accountability_result: Complete TrustChain result

        Returns:
            Dictionary containing the audit report
        """
        logger.info(f"Generating {self.format_type} audit report...")

        if self.format_type == "summary":
            return self._generate_summary(accountability_result)
        elif self.format_type == "compliance":
            return self._generate_compliance(accountability_result)
        else:
            return self._generate_full(accountability_result)

    def _generate_full(self, result: AccountabilityResult) -> Dict[str, Any]:
        """Generate full audit report with all details."""
        report = {
            "audit_report": {
                "generated_at": datetime.now().isoformat(),
                "report_type": "full_internal_audit",
                "version": self.version,
            },
            "identification": {
                "result_id": result.result_id,
                "case_id": result.case_id,
                "decision_type": result.decision_type,
                "timestamp": result.timestamp.isoformat(),
            },
            "decision": {
                "final_decision": result.final_decision.value,
                "overall_confidence": result.overall_confidence,
                "requires_human_review": result.requires_human_review,
                "review_triggers": [t.value for t in result.review_triggers],
            },
            "reasoning": {
                "primary_reasoning": result.primary_reasoning,
                "supporting_factors": result.supporting_factors,
                "concerns": result.concerns,
            },
            "strategy_execution": self._format_strategy_result(result),
            "analysis_results": self._format_analysis_results(result),
            "audit_trail": {
                "input_data_hash": result.input_data_hash,
                "audit_hash": result.audit_hash,
                "integrity_verified": result.verify_integrity() if result.audit_hash else None,
            },
        }

        if self.include_config_snapshot:
            report["configuration"] = result.config_snapshot

        if self.include_raw_responses and result.strategy_result:
            report["raw_responses"] = result.strategy_result.raw_responses

        logger.info(f"Generated full audit report for {result.result_id}")
        return report

    def _generate_summary(self, result: AccountabilityResult) -> Dict[str, Any]:
        """Generate summary audit report."""
        return {
            "audit_summary": {
                "generated_at": datetime.now().isoformat(),
                "result_id": result.result_id,
                "case_id": result.case_id,
                "decision_type": result.decision_type,
                "final_decision": result.final_decision.value,
                "confidence": result.overall_confidence,
                "requires_review": result.requires_human_review,
                "review_triggers": [t.value for t in result.review_triggers],
                "analysis_passed": all(
                    ar.passed for ar in result.analysis_results
                ),
                "audit_hash": result.audit_hash,
            }
        }

    def _generate_compliance(self, result: AccountabilityResult) -> Dict[str, Any]:
        """Generate compliance-focused audit report."""
        # Count bias-related findings
        bias_findings = []
        safety_findings = []

        for ar in result.analysis_results:
            if ar.detected_attributes:
                bias_findings.extend(ar.detected_attributes)
            if ar.flags:
                safety_findings.extend(ar.flags)

        return {
            "compliance_report": {
                "generated_at": datetime.now().isoformat(),
                "report_type": "regulatory_compliance",
            },
            "case_identification": {
                "result_id": result.result_id,
                "case_id": result.case_id,
                "decision_type": result.decision_type,
                "decision_timestamp": result.timestamp.isoformat(),
            },
            "decision_outcome": {
                "automated_decision": result.final_decision.value,
                "confidence_level": result.overall_confidence,
                "human_review_required": result.requires_human_review,
                "review_reasons": [t.value for t in result.review_triggers],
            },
            "bias_assessment": {
                "protected_attributes_detected": bias_findings,
                "bias_detected": len(bias_findings) > 0,
                "safety_concerns": safety_findings,
            },
            "model_agreement": {
                "agreement_level": result.strategy_result.agreement_level if result.strategy_result else None,
                "models_consulted": len(result.strategy_result.model_decisions) if result.strategy_result else 0,
                "dissenting_models": result.strategy_result.dissenting_views if result.strategy_result else [],
            },
            "explainability": {
                "primary_reasoning": result.primary_reasoning,
                "supporting_factors": result.supporting_factors,
                "concerns_raised": result.concerns,
            },
            "audit_integrity": {
                "input_hash": result.input_data_hash,
                "result_hash": result.audit_hash,
                "tamper_check": "PASSED" if result.verify_integrity() else "FAILED" if result.audit_hash else "NOT_COMPUTED",
            },
            "recommendations": self._generate_compliance_recommendations(result),
        }

    def _format_strategy_result(self, result: AccountabilityResult) -> Dict[str, Any]:
        """Format strategy result for audit report."""
        if not result.strategy_result:
            return {"status": "no_strategy_executed"}

        sr = result.strategy_result
        return {
            "strategy_name": sr.strategy_name,
            "decision": sr.decision.value,
            "confidence": sr.confidence,
            "reasoning": sr.reasoning,
            "agreement_level": sr.agreement_level,
            "model_count": len(sr.model_decisions),
            "model_decisions": [
                {
                    "provider": d.get("provider") if isinstance(d, dict) else getattr(d, "provider", "unknown"),
                    "decision": d.get("decision") if isinstance(d, dict) else getattr(d, "decision", "unknown"),
                    "confidence": d.get("confidence") if isinstance(d, dict) else getattr(d, "confidence", 0),
                }
                for d in sr.model_decisions
            ],
            "dissenting_views": sr.dissenting_views,
            "latency_ms": sr.latency_ms,
            "tokens_used": sr.tokens_used,
        }

    def _format_analysis_results(self, result: AccountabilityResult) -> List[Dict[str, Any]]:
        """Format analysis results for audit report."""
        formatted = []

        for ar in result.analysis_results:
            formatted.append({
                "analyzer_name": ar.analyzer_name,
                "passed": ar.passed,
                "flags": ar.flags,
                "warnings": ar.warnings,
                "detected_attributes": ar.detected_attributes,
                "detected_proxies": ar.detected_proxies,
                "recommendation": ar.recommendation,
            })

        return formatted

    def _generate_compliance_recommendations(
        self,
        result: AccountabilityResult
    ) -> List[str]:
        """Generate compliance recommendations based on findings."""
        recommendations = []

        if result.requires_human_review:
            recommendations.append(
                "Human review is required before this decision can be finalized."
            )

        for ar in result.analysis_results:
            if ar.detected_attributes:
                recommendations.append(
                    f"Review decision for potential discrimination based on: "
                    f"{', '.join(ar.detected_attributes)}"
                )

            if not ar.passed and ar.recommendation:
                recommendations.append(ar.recommendation)

        if result.overall_confidence < 0.7:
            recommendations.append(
                "Low confidence score suggests additional information may be needed."
            )

        if not recommendations:
            recommendations.append(
                "No compliance concerns identified. Standard processing may proceed."
            )

        return recommendations

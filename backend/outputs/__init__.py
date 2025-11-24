"""
TrustChain Output Generators

Outputs format accountability results for specific audiences:

- internal_audit: Detailed logs for compliance teams
- consumer_explanation: Plain-language summaries for applicants (Phase 2)
- compliance_report: Formatted reports for regulators (Phase 2)
- training_signal: Feedback for model improvement (Phase 2)
- appeal_package: Documentation for appeals process (Phase 2)

Usage:
    from outputs import InternalAuditOutput

    output = InternalAuditOutput(config={
        "include_raw_responses": False
    })
    formatted = output.generate(accountability_result)

Built with care by Kareem & Claude
"""

from core.base import BaseOutput
from core.registry import register_component

# Import outputs here as they're implemented
from .internal_audit import InternalAuditOutput
from .consumer_explanation import ConsumerExplanationOutput

__all__ = [
    "BaseOutput",
    "InternalAuditOutput",
    "ConsumerExplanationOutput",
]

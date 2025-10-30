"""
Orchestrator test with Anthropic only.

Since OpenAI needs billing setup, this tests with just Claude.
"""

import asyncio
import os
import json
from dotenv import load_dotenv

from providers import ProviderConfig
from services import DecisionOrchestrator

load_dotenv()


# Simplified test case
TEST_CASE = {
    "case_id": "unemp_demo_001",
    "name": "Standard Approval Case",
    "description": "Clear eligibility - should approve",
    "input_data": {
        "applicant_id": "A12345",
        "employment_duration_months": 18,
        "termination_reason": "company_layoff",
        "prior_earnings_annual": 45000,
        "available_for_work": True,
        "actively_seeking_work": True,
        "refused_suitable_work": False
    },
    "prompt": """
Unemployment Benefits Application - Case #unemp_demo_001

Applicant Details:
- Employment Duration: 18 months
- Reason for Separation: Company layoff
- Prior Annual Earnings: $45,000
- Available for Work: Yes
- Actively Seeking Employment: Yes

Please evaluate and provide:
1. Your decision (APPROVE or DENY)
2. Step-by-step reasoning
3. Your confidence level
"""
}

POLICY_CONTEXT = """
You are evaluating unemployment insurance applications.

ELIGIBILITY CRITERIA:
1. Employment Duration: Minimum 12 months
2. Separation Reason: Must be involuntary (layoff, not voluntary quit)
3. Availability: Must be available for work
4. Job Search: Must be actively seeking employment

DECISION:
- APPROVE: Meets all criteria
- DENY: Fails one or more criteria
"""


async def main():
    """Run demo with Anthropic only."""
    print("\n" + "="*80)
    print("TrustChain Demo - Single Provider (Anthropic Claude)")
    print("="*80)

    # Initialize with only Anthropic
    anthropic_config = ProviderConfig(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_retries=2,
        timeout_seconds=30
    )

    orchestrator = DecisionOrchestrator(
        anthropic_config=anthropic_config,
        # Note: Only 1 provider, so consensus is automatic
        require_consensus_threshold=0.5
    )

    print("\n✅ Orchestrator initialized with 1 provider (Anthropic Claude Haiku)")
    print("\n" + "="*80)
    print(f"Test Case: {TEST_CASE['name']}")
    print("="*80)
    print(f"\nDescription: {TEST_CASE['description']}")
    print(f"\nInput Data:")
    print(json.dumps(TEST_CASE['input_data'], indent=2))

    print("\n🚀 Submitting to orchestrator...")

    decision = await orchestrator.make_decision(
        case_id=TEST_CASE['case_id'],
        decision_type="unemployment_benefits",
        prompt=TEST_CASE['prompt'],
        policy_context=POLICY_CONTEXT,
        input_data=TEST_CASE['input_data']
    )

    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    print(f"\n📊 Decision ID: {decision.decision_id}")
    print(f"📋 Status: {decision.status.value.upper()}")
    print(f"🎯 Final Decision: {decision.final_decision.value.upper()}")

    if decision.consensus_analysis:
        print(f"\n🤝 Consensus Analysis:")
        print(f"   Agreement Level: {decision.consensus_analysis.agreement_level:.0%}")
        print(f"   Majority Decision: {decision.consensus_analysis.majority_decision.value}")

    # Show bias detection
    if decision.bias_analysis:
        print(f"\n🛡️  Bias & Safety Analysis:")
        print(f"   Bias Detected: {'YES ⚠️' if decision.bias_analysis.bias_detected else 'NO ✓'}")
        if decision.bias_analysis.bias_type:
            print(f"   Bias Type: {decision.bias_analysis.bias_type}")
        if decision.bias_analysis.affected_attributes:
            print(f"   Protected Attributes: {decision.bias_analysis.affected_attributes}")
        print(f"   Safety Confidence: {decision.bias_analysis.confidence:.2f}")

    print(f"\n🤖 Model Decision:")
    for model in decision.model_decisions:
        print(f"\n   {model.model_provider.upper()} ({model.model_name}):")
        print(f"   ├─ Decision: {model.decision.value}")
        print(f"   ├─ Confidence: {model.confidence:.2f}")
        print(f"   ├─ Tokens: {model.tokens_used}")
        print(f"   ├─ Latency: {model.latency_ms:.0f}ms")
        print(f"   └─ Reasoning: {model.reasoning[:200]}...")

    print(f"\n🔒 Audit Hash: {decision.audit_hash}")
    print(f"✓ Hash Valid: {decision.verify_audit_hash()}")

    print("\n" + "="*80)
    print("✅ Demo Complete!")
    print("="*80)
    print("\n💡 What just happened:")
    print("   1. Submitted case to Claude (Haiku model)")
    print("   2. Claude analyzed eligibility criteria")
    print("   3. Bias detection scanned for protected attributes")
    print("   4. Generated immutable audit hash (SHA-256)")
    print("   5. Decision ready for approval or human review")

    print("\n🎯 Key Features Demonstrated:")
    print("   ✓ Real AI decision-making")
    print("   ✓ Structured reasoning extraction")
    print("   ✓ Bias detection & safety checks")
    print("   ✓ Audit trail with tamper detection")
    print("   ✓ Confidence scoring")

    print("\n📝 Next Steps:")
    print("   - Add OpenAI billing to test multi-model consensus")
    print("   - Install Ollama to test local Llama")
    print("   - Run the API server: uvicorn app:app --reload")
    print("   - Test via HTTP: python test_api.py")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())

"""
Test script for TrustChain Orchestrator - Unemployment Benefits Demo

This demonstrates the complete decision flow:
1. Set up the orchestrator with multiple AI models
2. Submit an unemployment benefits application
3. Get consensus decision from all models
4. Display results with audit trail

Usage:
    python test_orchestrator.py
"""

import asyncio
import os
import json
from dotenv import load_dotenv

from providers import ProviderConfig
from services import DecisionOrchestrator

# Load environment variables
load_dotenv()


# Unemployment benefits test cases
TEST_CASES = [
    {
        "case_id": "unemp_001",
        "name": "Strong Approval Case",
        "description": "Clear eligibility - should get high consensus for APPROVAL",
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
        Unemployment Benefits Application - Case #unemp_001

        Applicant Details:
        - Employment Duration: 18 months at previous employer
        - Reason for Separation: Company-wide layoff due to business restructuring
        - Prior Annual Earnings: $45,000
        - Currently Available for Work: Yes
        - Actively Seeking Employment: Yes
        - Has Refused Suitable Work Offers: No

        Please evaluate this application and provide:
        1. Your decision (APPROVE or DENY)
        2. Step-by-step reasoning
        3. Your confidence level
        """
    },
    {
        "case_id": "unemp_002",
        "name": "Clear Denial Case",
        "description": "Voluntary quit - should get high consensus for DENIAL",
        "input_data": {
            "applicant_id": "A12346",
            "employment_duration_months": 24,
            "termination_reason": "voluntary_resignation",
            "prior_earnings_annual": 50000,
            "available_for_work": True,
            "actively_seeking_work": True,
            "refused_suitable_work": False
        },
        "prompt": """
        Unemployment Benefits Application - Case #unemp_002

        Applicant Details:
        - Employment Duration: 24 months at previous employer
        - Reason for Separation: Voluntary resignation to pursue other opportunities
        - Prior Annual Earnings: $50,000
        - Currently Available for Work: Yes
        - Actively Seeking Employment: Yes
        - Has Refused Suitable Work Offers: No

        Please evaluate this application and provide:
        1. Your decision (APPROVE or DENY)
        2. Step-by-step reasoning
        3. Your confidence level
        """
    },
    {
        "case_id": "unemp_003",
        "name": "Borderline Case",
        "description": "Ambiguous situation - might trigger human review",
        "input_data": {
            "applicant_id": "A12347",
            "employment_duration_months": 11,
            "termination_reason": "mutual_agreement",
            "prior_earnings_annual": 35000,
            "available_for_work": True,
            "actively_seeking_work": True,
            "refused_suitable_work": True,
            "refused_work_reason": "job_required_relocation_300_miles"
        },
        "prompt": """
        Unemployment Benefits Application - Case #unemp_003

        Applicant Details:
        - Employment Duration: 11 months at previous employer (just under 1 year threshold)
        - Reason for Separation: Mutual agreement termination
        - Prior Annual Earnings: $35,000
        - Currently Available for Work: Yes
        - Actively Seeking Employment: Yes
        - Has Refused Suitable Work Offers: Yes
          └─ Reason: Offered position required relocation 300 miles away

        Please evaluate this application and provide:
        1. Your decision (APPROVE or DENY)
        2. Step-by-step reasoning
        3. Your confidence level
        """
    }
]

# Policy context (same for all cases)
POLICY_CONTEXT = """
You are evaluating unemployment insurance applications based on state eligibility requirements.

ELIGIBILITY CRITERIA:
1. Employment Duration: Minimum 12 months of employment in the base period
2. Separation Reason: Must be involuntary (layoff, termination without cause)
   - DISQUALIFYING: Voluntary quit, fired for misconduct
   - QUALIFYING: Layoff, business closure, reduction in force
3. Availability: Must be available and able to work
4. Job Search: Must be actively seeking employment
5. Suitable Work: Cannot refuse suitable work without good cause
   - Good cause includes: unsafe conditions, significant wage reduction, unreasonable distance

DECISION GUIDELINES:
- APPROVE: Applicant meets all eligibility criteria
- DENY: Applicant fails one or more critical criteria
- NEEDS_REVIEW: Unclear or borderline case requiring human judgment

Provide clear reasoning for your decision, citing specific criteria.
"""


async def run_test_case(orchestrator, test_case):
    """Run a single test case through the orchestrator."""
    print("\n" + "="*80)
    print(f"TEST CASE: {test_case['name']}")
    print("="*80)
    print(f"Description: {test_case['description']}")
    print(f"Case ID: {test_case['case_id']}")
    print("\nInput Data:")
    print(json.dumps(test_case['input_data'], indent=2))

    # Make the decision
    print("\n🚀 Submitting to orchestrator...")
    decision = await orchestrator.make_decision(
        case_id=test_case['case_id'],
        decision_type="unemployment_benefits",
        prompt=test_case['prompt'],
        policy_context=POLICY_CONTEXT,
        input_data=test_case['input_data']
    )

    # Display results
    print("\n" + "─"*80)
    print("RESULTS")
    print("─"*80)

    print(f"\n📊 Decision ID: {decision.decision_id}")
    print(f"📋 Status: {decision.status.value}")
    print(f"🎯 Final Decision: {decision.final_decision.value.upper()}")

    if decision.consensus_analysis:
        print(f"\n🤝 Consensus Analysis:")
        print(f"   Agreement Level: {decision.consensus_analysis.agreement_level:.0%}")
        print(f"   Majority Decision: {decision.consensus_analysis.majority_decision.value}")
        print(f"   Dissenting Models: {decision.consensus_analysis.dissenting_models or 'None'}")
        print(f"   Confidence Variance: {decision.consensus_analysis.confidence_variance:.4f}")

        if decision.consensus_analysis.reasoning_divergence:
            print(f"\n⚠️  Reasoning Divergence:")
            print(f"   {decision.consensus_analysis.reasoning_divergence}")

    # Display bias detection results
    if decision.bias_analysis:
        print(f"\n🛡️  Bias & Safety Analysis:")
        print(f"   Bias Detected: {'YES ⚠️' if decision.bias_analysis.bias_detected else 'NO ✓'}")
        if decision.bias_analysis.bias_type:
            print(f"   Bias Type: {decision.bias_analysis.bias_type}")
        if decision.bias_analysis.affected_attributes:
            print(f"   Protected Attributes Found: {decision.bias_analysis.affected_attributes}")
        print(f"   Safety Confidence: {decision.bias_analysis.confidence:.2f}")
        if decision.bias_analysis.recommendation:
            print(f"\n   🔔 Recommendation:")
            print(f"   {decision.bias_analysis.recommendation}")

    print(f"\n🤖 Individual Model Decisions:")
    for model_decision in decision.model_decisions:
        print(f"\n   {model_decision.model_provider.upper()} ({model_decision.model_name}):")
        print(f"   ├─ Decision: {model_decision.decision.value}")
        print(f"   ├─ Confidence: {model_decision.confidence:.2f}")
        print(f"   ├─ Tokens: {model_decision.tokens_used}")
        print(f"   ├─ Latency: {model_decision.latency_ms:.0f}ms")
        print(f"   └─ Reasoning: {model_decision.reasoning[:150]}...")

    print(f"\n🔒 Audit Hash: {decision.audit_hash}")
    print(f"✓ Hash Valid: {decision.verify_audit_hash()}")

    if decision.status.value == "requires_review":
        print(f"\n⚠️  ⚠️  ⚠️  HUMAN REVIEW REQUIRED ⚠️  ⚠️  ⚠️")
        print(f"Reason: Consensus below threshold ({decision.consensus_analysis.agreement_level:.0%} < 66%)")

    return decision


async def main():
    """Run the unemployment benefits demo."""
    print("\n" + "="*80)
    print("TrustChain Orchestrator - Unemployment Benefits Demo")
    print("="*80)

    # Initialize provider configurations
    print("\n📡 Initializing AI providers...")

    anthropic_config = None
    openai_config = None
    llama_config = None

    # Configure Anthropic if API key is available
    if os.getenv("ANTHROPIC_API_KEY"):
        anthropic_config = ProviderConfig(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_retries=2,
            timeout_seconds=30
        )
        print("✓ Anthropic (Claude) configured")
    else:
        print("⚠️  Anthropic API key not found - skipping")

    # Configure OpenAI if API key is available
    if os.getenv("OPENAI_API_KEY"):
        openai_config = ProviderConfig(
            api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=2,
            timeout_seconds=30
        )
        print("✓ OpenAI (GPT) configured")
    else:
        print("⚠️  OpenAI API key not found - skipping")

    # Configure Llama/Ollama if available
    try:
        llama_config = ProviderConfig(
            max_retries=1,
            timeout_seconds=60
        )
        print("✓ Llama (Ollama) configured")
    except:
        print("⚠️  Ollama not available - skipping")

    # Create orchestrator
    orchestrator = DecisionOrchestrator(
        anthropic_config=anthropic_config,
        openai_config=openai_config,
        llama_config=llama_config,
        require_consensus_threshold=0.66
    )

    # Check provider health
    print("\n🏥 Provider Health Check:")
    health = orchestrator.get_provider_health()
    print(f"   Total Providers: {health['total_providers']}")
    print(f"   Healthy Providers: {health['healthy_providers']}")
    print(f"   Overall Health: {health['overall_health']:.0%}")

    if health['total_providers'] < 2:
        print("\n⚠️  Warning: Only 1 provider configured. Consensus requires at least 2.")
        print("   Add API keys to .env to enable more providers.")

    # Run test cases
    print("\n" + "="*80)
    print("Running Test Cases")
    print("="*80)

    results = []
    for test_case in TEST_CASES:
        try:
            decision = await run_test_case(orchestrator, test_case)
            results.append({
                "case": test_case['name'],
                "decision": decision.final_decision.value,
                "consensus": decision.consensus_analysis.agreement_level,
                "requires_review": decision.status.value == "requires_review"
            })
        except Exception as e:
            print(f"\n❌ Test case failed: {str(e)}")
            results.append({
                "case": test_case['name'],
                "decision": "ERROR",
                "consensus": 0,
                "requires_review": True
            })

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for result in results:
        status_icon = "⚠️" if result['requires_review'] else "✅"
        print(f"\n{status_icon} {result['case']}")
        print(f"   Decision: {result['decision'].upper()}")
        print(f"   Consensus: {result['consensus']:.0%}")
        print(f"   Review Needed: {result['requires_review']}")

    print("\n" + "="*80)
    print("🎉 Demo Complete!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

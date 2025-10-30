"""
API Test Client for TrustChain

This script demonstrates how to use the TrustChain API via HTTP requests.

Prerequisites:
    1. Start the API server: uvicorn app:app --reload
    2. Server runs on http://localhost:8000

Usage:
    python test_api.py
"""

import requests
import json
import time
from typing import Dict, Any


# API Configuration
API_BASE_URL = "http://localhost:8000"
API_V1 = f"{API_BASE_URL}/api/v1"


def check_health() -> Dict[str, Any]:
    """Check if API is healthy and providers are ready."""
    print("\n" + "="*80)
    print("🏥 Health Check")
    print("="*80)

    response = requests.get(f"{API_V1}/health")

    if response.status_code == 200:
        health = response.json()
        print(f"✅ API Status: {health['status']}")
        print(f"📊 Providers: {health['providers']['healthy_providers']}/{health['providers']['total_providers']} healthy")
        print(f"📈 Overall Health: {health['providers']['overall_health']:.0%}")
        print(f"📝 Decisions Processed: {health['decisions_processed']}")
        return health
    else:
        print(f"❌ Health check failed: {response.status_code}")
        print(response.text)
        return {}


def get_provider_status() -> Dict[str, Any]:
    """Get detailed provider status."""
    print("\n" + "="*80)
    print("🤖 Provider Status")
    print("="*80)

    response = requests.get(f"{API_V1}/providers/status")

    if response.status_code == 200:
        status_data = response.json()
        print(f"\nTotal Providers: {status_data['total_providers']}")
        print(f"Healthy: {status_data['healthy_providers']}")
        print(f"Overall Health: {status_data['overall_health']:.0%}\n")

        for provider in status_data['providers']:
            print(f"{provider['provider'].upper()}")
            print(f"  Status: {provider['status']}")
            print(f"  Requests: {provider['total_requests']}")
            print(f"  Errors: {provider['total_errors']}")
            print(f"  Error Rate: {provider['error_rate']:.1%}")
            print(f"  Health Score: {provider['health_score']:.0%}\n")

        return status_data
    else:
        print(f"❌ Provider status failed: {response.status_code}")
        return {}


def submit_decision(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Submit a decision request to the API."""
    print("\n" + "="*80)
    print(f"📤 Submitting Decision: {case_data['case_id']}")
    print("="*80)

    print("\nRequest Data:")
    print(json.dumps(case_data, indent=2))

    start_time = time.time()

    response = requests.post(
        f"{API_V1}/decisions",
        json=case_data,
        headers={"Content-Type": "application/json"}
    )

    elapsed_time = time.time() - start_time

    if response.status_code == 201:
        decision = response.json()
        print(f"\n✅ Decision Created (took {elapsed_time:.2f}s)")
        print(f"\n📊 Results:")
        print(f"  Decision ID: {decision['decision_id']}")
        print(f"  Status: {decision['status']}")
        print(f"  Final Decision: {decision['final_decision'].upper()}")
        print(f"  Requires Review: {decision['requires_human_review']}")

        if decision.get('consensus_analysis'):
            print(f"\n🤝 Consensus:")
            print(f"  Agreement: {decision['consensus_analysis']['agreement_level']:.0%}")
            print(f"  Majority: {decision['consensus_analysis']['majority_decision']}")
            print(f"  Dissenting: {decision['consensus_analysis']['dissenting_models'] or 'None'}")

        print(f"\n🤖 Model Decisions:")
        for model in decision['model_decisions']:
            print(f"  {model['model_provider'].upper()}: {model['decision']} ({model['confidence']:.0%} confidence)")

        print(f"\n🔒 Audit Hash: {decision['audit_hash'][:16]}...")

        return decision
    else:
        print(f"\n❌ Decision failed: {response.status_code}")
        print(response.text)
        return {}


def get_decision(decision_id: str) -> Dict[str, Any]:
    """Retrieve a decision by ID."""
    print("\n" + "="*80)
    print(f"📥 Retrieving Decision: {decision_id}")
    print("="*80)

    response = requests.get(f"{API_V1}/decisions/{decision_id}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Decision Found")
        print(f"  Audit Verified: {data['audit_verified']}")

        decision = data['decision']
        print(f"\n📊 Summary:")
        print(f"  Case ID: {decision['case_id']}")
        print(f"  Type: {decision['decision_type']}")
        print(f"  Final Decision: {decision['final_decision']}")
        print(f"  Status: {decision['status']}")
        print(f"  Created: {decision['created_at']}")

        if data.get('foia_report'):
            print(f"\n📄 FOIA Report:")
            print(json.dumps(data['foia_report'], indent=2))

        return data
    else:
        print(f"❌ Retrieval failed: {response.status_code}")
        return {}


def list_decisions() -> Dict[str, Any]:
    """List all decisions."""
    print("\n" + "="*80)
    print("📋 Listing Recent Decisions")
    print("="*80)

    response = requests.get(f"{API_V1}/decisions?limit=10")

    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal Decisions: {data['total']}")
        print(f"Showing: {data['filtered']}\n")

        for decision in data['decisions']:
            review_flag = "⚠️ REVIEW" if decision['requires_review'] else "✓"
            print(f"{review_flag} {decision['decision_id']}")
            print(f"  Case: {decision['case_id']}")
            print(f"  Type: {decision['decision_type']}")
            print(f"  Decision: {decision['final_decision'] or 'PENDING'}")
            print(f"  Consensus: {decision['consensus_level']:.0%}" if decision['consensus_level'] else "  Consensus: N/A")
            print(f"  Created: {decision['created_at']}\n")

        return data
    else:
        print(f"❌ List failed: {response.status_code}")
        return {}


# ============================================================================
# TEST CASES
# ============================================================================

UNEMPLOYMENT_APPROVAL_CASE = {
    "case_id": "api_test_001",
    "decision_type": "unemployment_benefits",
    "input_data": {
        "employment_duration_months": 18,
        "termination_reason": "company_layoff",
        "prior_earnings_annual": 45000,
        "available_for_work": True,
        "actively_seeking_work": True,
        "refused_suitable_work": False
    },
    "policy_context": """
State unemployment eligibility requirements:
1. Minimum 12 months employment
2. Involuntary separation (layoff, not fired for cause)
3. Available and seeking work
4. Sufficient prior earnings

Decision: APPROVE if meets all criteria, DENY otherwise.
""",
    "require_consensus": True
}

UNEMPLOYMENT_DENIAL_CASE = {
    "case_id": "api_test_002",
    "decision_type": "unemployment_benefits",
    "input_data": {
        "employment_duration_months": 8,  # Under 12 months threshold
        "termination_reason": "voluntary_resignation",
        "prior_earnings_annual": 35000,
        "available_for_work": True,
        "actively_seeking_work": True,
        "refused_suitable_work": False
    },
    "policy_context": """
State unemployment eligibility requirements:
1. Minimum 12 months employment
2. Involuntary separation (layoff, not fired for cause)
3. Available and seeking work

Decision: APPROVE if meets all criteria, DENY otherwise.
""",
    "require_consensus": True
}


def main():
    """Run API tests."""
    print("\n" + "="*80)
    print("TrustChain API Test Suite")
    print("="*80)
    print("\nMake sure the API server is running:")
    print("  uvicorn app:app --reload")
    print("\nAPI Base URL:", API_BASE_URL)
    print("="*80)

    # Wait for user confirmation
    input("\nPress Enter to start tests...")

    # Test 1: Health Check
    health = check_health()
    if not health or health.get('status') != 'healthy':
        print("\n⚠️  API is not healthy. Check server logs.")
        return

    # Test 2: Provider Status
    get_provider_status()

    # Test 3: Submit approval case
    print("\n" + "="*80)
    print("TEST CASE 1: Strong Approval")
    print("="*80)
    decision1 = submit_decision(UNEMPLOYMENT_APPROVAL_CASE)

    if decision1:
        # Retrieve the decision
        get_decision(decision1['decision_id'])

    # Test 4: Submit denial case
    print("\n" + "="*80)
    print("TEST CASE 2: Clear Denial")
    print("="*80)
    decision2 = submit_decision(UNEMPLOYMENT_DENIAL_CASE)

    # Test 5: List all decisions
    list_decisions()

    # Summary
    print("\n" + "="*80)
    print("🎉 API Tests Complete!")
    print("="*80)
    print("\nYou can now:")
    print("  1. View interactive docs: http://localhost:8000/docs")
    print("  2. Submit your own cases via HTTP POST")
    print("  3. Retrieve decisions via HTTP GET")
    print("  4. Integrate with frontend application")
    print("\n" + "="*80)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to API server!")
        print("Make sure the server is running:")
        print("  cd backend")
        print("  uvicorn app:app --reload")
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")

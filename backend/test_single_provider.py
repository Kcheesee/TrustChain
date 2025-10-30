"""
Simple test with just Anthropic (Claude)

This tests the system with a single provider to verify everything works.
"""

import asyncio
import os
from dotenv import load_dotenv

from providers import ProviderConfig, AnthropicProvider

load_dotenv()


async def test_claude():
    """Test just Claude."""
    print("="*80)
    print("Testing Claude (Anthropic) Provider")
    print("="*80)

    config = ProviderConfig(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_retries=2,
        timeout_seconds=30
    )

    provider = AnthropicProvider(config=config)

    print(f"\n✓ Provider initialized with model: {provider.model}")

    # Simple test prompt
    prompt = """
    An applicant for unemployment benefits:
    - Worked 18 months
    - Laid off due to company closure
    - Available for work
    - Seeking employment

    Should this be APPROVED or DENIED for unemployment benefits?
    Provide brief reasoning.
    """

    print("\n📡 Sending request to Claude...")

    response = await provider.generate_decision(
        prompt=prompt,
        system_context="Evaluate unemployment benefit eligibility. Minimum 12 months employment required."
    )

    print(f"\n✅ Response received!")
    print(f"   Model: {response.model_name}")
    print(f"   Confidence: {response.confidence:.2f}")
    print(f"   Tokens: {response.tokens_used}")
    print(f"   Latency: {response.latency_ms:.0f}ms")
    print(f"\n   Content:\n   {response.content[:300]}...")

    if response.reasoning:
        print(f"\n   Reasoning:\n   {response.reasoning[:200]}...")

    print("\n" + "="*80)
    print("✅ Test Complete!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_claude())

"""
Test script for TrustChain LLM providers.

This script tests each provider individually to verify API connectivity
and proper response handling. Run this before building the orchestrator.

Usage:
    python test_providers.py
"""

import asyncio
import os
from dotenv import load_dotenv

from providers import (
    AnthropicProvider,
    OpenAIProvider,
    LlamaProvider,
    ProviderConfig
)

# Load environment variables
load_dotenv()


async def test_anthropic():
    """Test Anthropic Claude provider."""
    print("\n" + "="*60)
    print("Testing Anthropic Claude Provider")
    print("="*60)

    try:
        config = ProviderConfig(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_retries=2,
            timeout_seconds=30
        )

        provider = AnthropicProvider(config=config)

        # Validate API key
        print("✓ Validating API key...")
        is_valid = await provider.validate_api_key()
        print(f"✓ API key valid: {is_valid}")

        # Test decision generation
        print("\n✓ Testing decision generation...")
        prompt = """
        An applicant for unemployment benefits has the following information:
        - Employment duration: 18 months
        - Reason for separation: Company layoff
        - Prior earnings: $45,000/year
        - Available for work: Yes

        Should this application be approved or denied based on standard
        unemployment eligibility criteria?
        """

        system_context = """
        You are evaluating unemployment benefit applications.
        Standard eligibility requires:
        1. Minimum 12 months employment
        2. Involuntary separation (not fired for cause)
        3. Available and seeking work
        4. Sufficient prior earnings
        """

        response = await provider.generate_decision(
            prompt=prompt,
            system_context=system_context
        )

        print(f"\n✓ Decision received:")
        print(f"  - Provider: {response.provider.value}")
        print(f"  - Model: {response.model_name}")
        print(f"  - Confidence: {response.confidence:.2f}")
        print(f"  - Tokens used: {response.tokens_used}")
        print(f"  - Latency: {response.latency_ms:.0f}ms")
        print(f"\n  Response excerpt: {response.content[:200]}...")

        if response.reasoning:
            print(f"\n  Reasoning excerpt: {response.reasoning[:200]}...")

        print("\n✅ Anthropic provider test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Anthropic provider test FAILED: {str(e)}")
        return False


async def test_openai():
    """Test OpenAI GPT provider."""
    print("\n" + "="*60)
    print("Testing OpenAI GPT Provider")
    print("="*60)

    try:
        config = ProviderConfig(
            api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=2,
            timeout_seconds=30
        )

        provider = OpenAIProvider(config=config)

        # Validate API key
        print("✓ Validating API key...")
        is_valid = await provider.validate_api_key()
        print(f"✓ API key valid: {is_valid}")

        # Test decision generation
        print("\n✓ Testing decision generation...")
        prompt = """
        An applicant for unemployment benefits has the following information:
        - Employment duration: 18 months
        - Reason for separation: Company layoff
        - Prior earnings: $45,000/year
        - Available for work: Yes

        Should this application be approved or denied based on standard
        unemployment eligibility criteria?
        """

        system_context = """
        You are evaluating unemployment benefit applications.
        Standard eligibility requires:
        1. Minimum 12 months employment
        2. Involuntary separation (not fired for cause)
        3. Available and seeking work
        4. Sufficient prior earnings
        """

        response = await provider.generate_decision(
            prompt=prompt,
            system_context=system_context
        )

        print(f"\n✓ Decision received:")
        print(f"  - Provider: {response.provider.value}")
        print(f"  - Model: {response.model_name}")
        print(f"  - Confidence: {response.confidence:.2f}")
        print(f"  - Tokens used: {response.tokens_used}")
        print(f"  - Latency: {response.latency_ms:.0f}ms")
        print(f"\n  Response excerpt: {response.content[:200]}...")

        if response.reasoning:
            print(f"\n  Reasoning excerpt: {response.reasoning[:200]}...")

        print("\n✅ OpenAI provider test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ OpenAI provider test FAILED: {str(e)}")
        return False


async def test_llama():
    """Test Llama/Ollama provider."""
    print("\n" + "="*60)
    print("Testing Llama/Ollama Provider")
    print("="*60)

    try:
        config = ProviderConfig(
            max_retries=2,
            timeout_seconds=60  # Longer timeout for local models
        )

        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        provider = LlamaProvider(
            config=config,
            ollama_base_url=ollama_url
        )

        # Validate Ollama is running
        print("✓ Checking Ollama availability...")
        is_valid = await provider.validate_api_key()
        print(f"✓ Ollama accessible: {is_valid}")

        # Test decision generation
        print("\n✓ Testing decision generation...")
        prompt = """
        An applicant for unemployment benefits has the following information:
        - Employment duration: 18 months
        - Reason for separation: Company layoff
        - Prior earnings: $45,000/year
        - Available for work: Yes

        Should this application be approved or denied based on standard
        unemployment eligibility criteria?
        """

        system_context = """
        You are evaluating unemployment benefit applications.
        Standard eligibility requires:
        1. Minimum 12 months employment
        2. Involuntary separation (not fired for cause)
        3. Available and seeking work
        4. Sufficient prior earnings
        """

        response = await provider.generate_decision(
            prompt=prompt,
            system_context=system_context
        )

        print(f"\n✓ Decision received:")
        print(f"  - Provider: {response.provider.value}")
        print(f"  - Model: {response.model_name}")
        print(f"  - Confidence: {response.confidence:.2f}")
        print(f"  - Tokens used: {response.tokens_used}")
        print(f"  - Latency: {response.latency_ms:.0f}ms")
        print(f"\n  Response excerpt: {response.content[:200]}...")

        if response.reasoning:
            print(f"\n  Reasoning excerpt: {response.reasoning[:200]}...")

        print("\n✅ Llama provider test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Llama provider test FAILED: {str(e)}")
        print(f"   Note: Ollama must be running locally. Install from https://ollama.ai")
        return False


async def main():
    """Run all provider tests."""
    print("\n" + "="*60)
    print("TrustChain Provider Test Suite")
    print("="*60)

    results = {}

    # Test each provider
    results['anthropic'] = await test_anthropic()
    results['openai'] = await test_openai()
    results['llama'] = await test_llama()

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for provider, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{provider.upper():12} : {status}")

    total_passed = sum(results.values())
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} providers working")

    if total_passed == total_tests:
        print("\n🎉 All providers operational!")
    elif total_passed > 0:
        print(f"\n⚠️  {total_tests - total_passed} provider(s) need attention")
    else:
        print("\n❌ No providers are working - check API keys and configuration")


if __name__ == "__main__":
    asyncio.run(main())

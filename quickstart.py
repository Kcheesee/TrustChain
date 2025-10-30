"""
TrustChain Quick Start Example

This is the FASTEST way to see TrustChain in action.
Run this after setup to verify everything works.

Prerequisites:
1. Virtual environment activated
2. Dependencies installed (pip install -r backend/requirements.txt)
3. .env file with ANTHROPIC_API_KEY set

Usage:
    python quickstart.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from providers import ProviderConfig, AnthropicProvider

# Load environment
load_dotenv(backend_path / ".env")


async def main():
    print("\n" + "="*70)
    print("🚀 TrustChain Quick Start")
    print("="*70)

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_anthropic_api_key_here":
        print("\n❌ ERROR: ANTHROPIC_API_KEY not set in backend/.env")
        print("\nPlease:")
        print("1. Copy backend/.env.example to backend/.env")
        print("2. Add your Anthropic API key")
        print("3. Run this script again")
        return

    print("\n✓ API key found")
    print("✓ Creating provider...")

    # Create provider
    config = ProviderConfig(api_key=api_key, timeout_seconds=30)
    provider = AnthropicProvider(config=config)

    print(f"✓ Using model: {provider.model}")

    # Simple test
    print("\n📡 Making test decision...")
    print("\nPrompt: 'Should we approve unemployment benefits for someone")
    print("        who worked 18 months and was laid off?'\n")

    response = await provider.generate_decision(
        prompt="""
        Should we approve unemployment benefits for an applicant who:
        - Worked for 18 months
        - Was laid off (company closure)
        - Is available for work
        - Is actively seeking employment

        Answer in one sentence.
        """,
        system_context="You evaluate unemployment benefit eligibility."
    )

    # Show results
    print("="*70)
    print("RESPONSE")
    print("="*70)
    print(f"\n✅ {response.content}\n")
    print(f"📊 Confidence: {response.confidence:.0%}")
    print(f"⚡ Response time: {response.latency_ms:.0f}ms")
    print(f"🔢 Tokens used: {response.tokens_used}")

    print("\n" + "="*70)
    print("🎉 TrustChain is working!")
    print("="*70)

    print("\n💡 Next steps:")
    print("   1. Run full tests: cd backend && python test_orchestrator_anthropic_only.py")
    print("   2. Start API server: cd backend && uvicorn app:app --reload")
    print("   3. View docs: http://localhost:8000/docs")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("\nCheck that:")
        print("  1. You're in the TrustChain directory")
        print("  2. Virtual environment is activated")
        print("  3. Dependencies are installed")
        print("  4. API key is set in backend/.env")

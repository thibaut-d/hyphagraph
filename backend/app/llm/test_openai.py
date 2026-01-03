"""
Test script for OpenAI provider.

Run this to verify OpenAI integration is working:
    uv run python -m app.llm.test_openai
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import settings
from app.llm.openai_provider import OpenAIProvider


async def test_basic_generation():
    """Test basic text generation."""
    print("=" * 60)
    print("Testing OpenAI Basic Generation")
    print("=" * 60)

    provider = OpenAIProvider()

    if not provider.is_available():
        print("❌ OpenAI provider not available - check OPENAI_API_KEY in .env")
        return False

    print(f"✓ Provider available")
    print(f"  Model: {provider.get_model_name()}")
    print(f"  API Key: {settings.OPENAI_API_KEY[:20]}..." if settings.OPENAI_API_KEY else "  API Key: None")
    print()

    try:
        print("Generating completion...")
        response = await provider.generate(
            prompt="What is aspirin used for? Answer in 1-2 sentences.",
            system_prompt="You are a helpful medical knowledge assistant.",
            temperature=0.3,
            max_tokens=100,
        )

        print(f"✓ Generation successful!")
        print(f"  Model: {response.model}")
        print(f"  Tokens: {response.usage['total_tokens']} ({response.usage['prompt_tokens']} prompt + {response.usage['completion_tokens']} completion)")
        print(f"\n  Response:\n  {response.content}\n")

        return True

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return False


async def test_json_generation():
    """Test JSON mode generation."""
    print("=" * 60)
    print("Testing OpenAI JSON Generation")
    print("=" * 60)

    provider = OpenAIProvider()

    if not provider.is_available():
        print("❌ OpenAI provider not available")
        return False

    try:
        print("Generating JSON...")
        result = await provider.generate_json(
            prompt="""
Extract key information about aspirin:
- name: drug name
- uses: list of common uses
- category: pharmacological category
""",
            system_prompt="You are a medical knowledge extraction assistant.",
            temperature=0.2,
            max_tokens=200,
        )

        print(f"✓ JSON generation successful!")
        print(f"\n  Parsed JSON:")
        import json
        print(json.dumps(result, indent=2))
        print()

        return True

    except Exception as e:
        print(f"❌ JSON generation failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("OpenAI Provider Test Suite")
    print("=" * 60 + "\n")

    test1 = await test_basic_generation()
    print()

    test2 = await test_json_generation()
    print()

    print("=" * 60)
    if test1 and test2:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

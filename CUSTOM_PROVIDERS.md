# Adding Custom LLM Providers to TrustChain

Complete guide for integrating new AI models into TrustChain's multi-model consensus system.

## Why Add Custom Providers?

- ✅ Use proprietary/internal LLMs
- ✅ Add support for Gemini, Cohere, Mistral, etc.
- ✅ Leverage specialized domain models
- ✅ Meet specific compliance requirements
- ✅ Optimize for cost or performance

## Quick Start (5 Minutes)

### 1. Copy the Template

```bash
cd backend/providers
cp custom_provider_template.py my_provider.py
```

### 2. Customize the Class

```python
# In my_provider.py
class MyProvider(CustomProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(
            config=config,
            model="my-model-name",
            provider_name="my_provider"
        )

        # Initialize your API client
        import your_sdk
        self.client = your_sdk.Client(api_key=config.api_key)
```

### 3. Implement API Call

```python
async def generate_decision(self, prompt, system_context=None, ...):
    # Make API call
    response = await self.client.generate(
        prompt=prompt,
        temperature=self.config.temperature
    )

    # Return structured response
    return LLMResponse(
        provider=ModelProvider("my_provider"),
        model_name=self.model,
        content=response.text,
        reasoning=self._extract_reasoning(response.text),
        confidence=self._calculate_confidence(response.text),
        timestamp=datetime.now()
    )
```

### 4. Register Provider

```python
# In your app.py or providers/__init__.py
from providers.my_provider import MyProvider
from providers import register_provider

register_provider(
    name="my_provider",
    provider_class=MyProvider,
    metadata={
        "description": "My Custom LLM",
        "models": ["model-v1", "model-v2"],
        "commercial_use": True
    }
)
```

### 5. Use in Decisions

```python
# In your API or orchestrator
from providers import get_global_registry, ProviderConfig

registry = get_global_registry()
config = ProviderConfig(api_key="your-key")

provider = registry.create_provider("my_provider", config)
response = await provider.generate_decision(
    prompt="Should this application be approved?"
)
```

---

## Step-by-Step Guide

### Step 1: Understand the Interface

All providers must implement `BaseLLMProvider`:

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_decision(
        self,
        prompt: str,
        system_context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Generate a decision using the LLM."""
        pass

    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """Check if provider is healthy."""
        pass
```

### Step 2: Implement Decision Parsing

TrustChain needs to extract:
1. **Decision**: "approve", "deny", or "needs_review"
2. **Reasoning**: Why the LLM made this decision
3. **Confidence**: 0.0 to 1.0 score

```python
def _parse_decision(self, response: str) -> str:
    """Extract decision from LLM response."""
    response_lower = response.lower()

    # Look for decision keywords
    if "approve" in response_lower:
        return "approve"
    elif "deny" in response_lower:
        return "deny"
    else:
        return "needs_review"

def _extract_reasoning(self, response: str) -> str:
    """Extract reasoning/explanation."""
    # Option 1: Look for specific sections
    if "Reasoning:" in response:
        return response.split("Reasoning:")[1].split("\n\n")[0]

    # Option 2: Return full response
    return response

def _calculate_confidence(self, response: str) -> float:
    """Calculate confidence score (0.0-1.0)."""
    # Option 1: Parse from response
    if "confidence: 0." in response.lower():
        # Extract confidence value

    # Option 2: Use API-provided logprobs
    # logprobs = self.client.get_logprobs(response)
    # return self._logprobs_to_confidence(logprobs)

    # Option 3: Keyword-based heuristic
    if "very confident" in response.lower():
        return 0.95
    elif "confident" in response.lower():
        return 0.85
    elif "uncertain" in response.lower():
        return 0.5
    else:
        return 0.7  # Default
```

### Step 3: Handle Errors Gracefully

```python
async def generate_decision(self, prompt, ...):
    try:
        # Make API call
        response = await self.client.generate(prompt)
        return self._format_response(response)

    except RateLimitError as e:
        logger.warning(f"Rate limited: {e}")
        # Return degraded response
        return LLMResponse(
            ...,
            confidence=0.0,
            error="Rate limit exceeded - retry later"
        )

    except APIError as e:
        logger.error(f"API error: {e}")
        return LLMResponse(..., error=str(e))

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return LLMResponse(..., error="Provider unavailable")
```

### Step 4: Implement Health Checks

```python
async def health_check(self) -> ProviderStatus:
    """Check if provider is responding."""
    try:
        # Make lightweight test call
        response = await self.client.test_connection()

        if response.status == "ok":
            return ProviderStatus.HEALTHY
        else:
            return ProviderStatus.DEGRADED

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ProviderStatus.UNAVAILABLE
```

---

## Real-World Examples

### Example 1: Google Gemini

```python
import google.generativeai as genai
from providers.custom_provider_template import CustomProvider

class GeminiProvider(CustomProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config, model="gemini-pro", provider_name="gemini")
        genai.configure(api_key=config.api_key)
        self.client = genai.GenerativeModel('gemini-pro')

    async def generate_decision(self, prompt, system_context=None, **kwargs):
        start_time = datetime.now()

        try:
            # Gemini API call
            response = await self.client.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=kwargs.get("temperature", 0.7),
                    max_output_tokens=kwargs.get("max_tokens", 2000)
                )
            )

            # Parse response
            text = response.text
            decision = self._parse_decision(text)
            reasoning = self._extract_reasoning(text)
            confidence = self._calculate_confidence(text)

            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            return LLMResponse(
                provider=ModelProvider("gemini"),
                model_name="gemini-pro",
                content=text,
                reasoning=reasoning,
                confidence=confidence,
                timestamp=datetime.now(),
                latency_ms=latency_ms,
                metadata={"safety_ratings": response.safety_ratings}
            )

        except Exception as e:
            return self._error_response(str(e))

# Register
register_provider("gemini", GeminiProvider, metadata={
    "description": "Google Gemini Pro",
    "models": ["gemini-pro", "gemini-ultra"],
    "commercial_use": True
})
```

### Example 2: Cohere Command

```python
import cohere
from providers.custom_provider_template import CustomProvider

class CohereProvider(CustomProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config, model="command", provider_name="cohere")
        self.client = cohere.AsyncClient(api_key=config.api_key)

    async def generate_decision(self, prompt, system_context=None, **kwargs):
        try:
            # Combine system context and prompt
            full_prompt = f"{system_context}\n\n{prompt}" if system_context else prompt

            # Cohere API call
            response = await self.client.generate(
                prompt=full_prompt,
                model="command",
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000)
            )

            text = response.generations[0].text

            return LLMResponse(
                provider=ModelProvider("cohere"),
                model_name="command",
                content=text,
                reasoning=self._extract_reasoning(text),
                confidence=self._calculate_confidence(text),
                timestamp=datetime.now(),
                metadata={
                    "likelihood": response.generations[0].likelihood
                }
            )

        except Exception as e:
            return self._error_response(str(e))

# Register
register_provider("cohere", CohereProvider, metadata={
    "description": "Cohere Command",
    "commercial_use": True
})
```

### Example 3: Custom Internal LLM

```python
from providers.custom_provider_template import CustomProvider

class InternalLLMProvider(CustomProvider):
    """
    Example: Proprietary internal LLM
    """
    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            model="internal-model-v2",
            provider_name="internal"
        )
        # Initialize internal API client
        self.client = InternalAPIClient(
            endpoint=config.base_url,
            auth_token=config.api_key
        )

    async def generate_decision(self, prompt, **kwargs):
        try:
            # Call internal API
            response = await self.client.infer(
                text=prompt,
                model_version="v2",
                temperature=kwargs.get("temperature", 0.7)
            )

            return LLMResponse(
                provider=ModelProvider("internal"),
                model_name="internal-model-v2",
                content=response["text"],
                reasoning=response.get("explanation"),
                confidence=response.get("confidence", 0.7),
                timestamp=datetime.now(),
                metadata={
                    "internal_id": response["request_id"],
                    "compliance_checked": True
                }
            )

        except Exception as e:
            return self._error_response(str(e))

# Register
register_provider("internal", InternalLLMProvider, metadata={
    "description": "Internal Proprietary LLM",
    "commercial_use": True,
    "privacy": "high",
    "on_premises": True
})
```

---

## Testing Your Provider

### Unit Tests

```python
# In backend/tests/test_my_provider.py
import pytest
from providers.my_provider import MyProvider
from providers import ProviderConfig

@pytest.fixture
def provider():
    config = ProviderConfig(api_key="test-key")
    return MyProvider(config)

@pytest.mark.asyncio
async def test_generate_decision(provider):
    response = await provider.generate_decision(
        prompt="Should this loan be approved?",
        system_context="You are a loan officer."
    )

    assert response.provider == "my_provider"
    assert response.confidence >= 0.0 and response.confidence <= 1.0
    assert response.content is not None
    assert response.reasoning is not None

@pytest.mark.asyncio
async def test_health_check(provider):
    status = await provider.health_check()
    assert status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED, ProviderStatus.UNAVAILABLE]
```

### Integration Testing

```python
# Test with orchestrator
from services.orchestrator import DecisionOrchestrator
from providers import ProviderConfig

orchestrator = DecisionOrchestrator(
    provider_configs={
        "anthropic": ProviderConfig(api_key=os.getenv("ANTHROPIC_API_KEY")),
        "my_provider": ProviderConfig(api_key=os.getenv("MY_PROVIDER_KEY"))
    }
)

decision = await orchestrator.make_decision(
    case_id="TEST-001",
    case_type="loan_application",
    decision_type="standard",
    context="Test case details..."
)

# Verify both providers participated
assert len(decision.model_decisions) >= 2
assert any(d.provider == "my_provider" for d in decision.model_decisions)
```

---

## Best Practices

### 1. Confidence Scoring

**Good:**
```python
def _calculate_confidence(self, response):
    # Use API-provided confidence if available
    if hasattr(response, 'confidence'):
        return response.confidence

    # Fall back to keyword analysis
    keywords = {
        "definitely": 0.95,
        "very confident": 0.9,
        "confident": 0.8,
        "likely": 0.7,
        "possibly": 0.5,
        "uncertain": 0.3
    }

    for keyword, score in keywords.items():
        if keyword in response.lower():
            return score

    return 0.7  # Conservative default
```

**Bad:**
```python
def _calculate_confidence(self, response):
    return 1.0  # Always maximum confidence (unrealistic!)
```

### 2. Error Handling

**Good:**
```python
try:
    response = await self.client.generate(prompt)
except SpecificAPIError as e:
    logger.error(f"API error: {e}")
    return LLMResponse(..., error=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return LLMResponse(..., error="Provider unavailable")
```

**Bad:**
```python
response = await self.client.generate(prompt)  # No error handling!
```

### 3. Audit Logging

**Good:**
```python
return LLMResponse(
    ...,
    metadata={
        "api_version": "v2",
        "request_id": response.id,
        "model_config": {"temperature": 0.7},
        "safety_check": "passed"
    }
)
```

**Bad:**
```python
return LLMResponse(..., metadata={})  # No audit trail!
```

---

## Troubleshooting

### Provider Not Found

```
KeyError: Provider 'my_provider' not found
```

**Solution:** Make sure you registered the provider:
```python
from providers import register_provider
from providers.my_provider import MyProvider

register_provider("my_provider", MyProvider)
```

### Confidence Always 0.0

**Problem:** Confidence calculation not implemented

**Solution:** Implement `_calculate_confidence()` method:
```python
def _calculate_confidence(self, response):
    # Don't just return 0.0!
    return 0.7  # At minimum, use a reasonable default
```

### Provider Initialization Fails

```
AttributeError: 'NoneType' object has no attribute 'generate'
```

**Solution:** Check your `__init__` method:
```python
def __init__(self, config):
    super().__init__(config, ...)

    # Initialize your client properly
    self.client = YourSDK.Client(api_key=config.api_key)
    # NOT: self.client = None
```

---

## Commercial Deployment

### For SaaS Applications

```python
# Multi-tenant provider configuration
class TenantProviderManager:
    def __init__(self):
        self.registry = get_global_registry()

    def get_tenant_provider(self, tenant_id, provider_name):
        # Load tenant-specific API keys from database
        config = self._load_tenant_config(tenant_id, provider_name)
        return self.registry.create_provider(provider_name, config)

# Usage
manager = TenantProviderManager()
provider = manager.get_tenant_provider("tenant_123", "gemini")
```

### For White-Label Solutions

```python
# Custom branding
register_provider(
    "your_brand_ai",
    YourProviderClass,
    metadata={
        "description": "YourBrand AI Decision Engine",
        "white_label": True,
        "customer_facing_name": "YourBrand Intelligence"
    }
)
```

---

## Support

### Community Support (Free)
- GitHub Discussions: https://github.com/Kcheesee/TrustChain/discussions
- Examples: See `backend/providers/custom_provider_template.py`

### Commercial Support
- Provider integration service: $2,500 one-time
- Priority support: Included with Business+ tier
- Custom development: Contact sales@trustchain.ai

---

## Next Steps

1. ✅ Copy `custom_provider_template.py`
2. ✅ Implement your provider
3. ✅ Add unit tests
4. ✅ Test with orchestrator
5. ✅ Deploy to production

**Need help?** Open an issue on GitHub or contact support!

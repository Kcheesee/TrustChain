"""
Provider Registry - Dynamic LLM Provider Management

Allows runtime registration and discovery of LLM providers,
making it easy to add support for new AI models without
modifying core orchestration code.
"""

from typing import Dict, Type, List, Optional
from .base import BaseLLMProvider, ProviderConfig, ModelProvider
import logging

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Central registry for LLM providers.

    Implements the Registry pattern to allow dynamic provider
    registration and discovery. Supports both built-in providers
    (Anthropic, OpenAI, Llama) and custom third-party providers.

    Example:
        # Register a custom provider
        registry = ProviderRegistry()
        registry.register("gemini", GeminiProvider)

        # Get provider class
        provider_class = registry.get("gemini")
        provider = provider_class(config)
    """

    def __init__(self):
        """Initialize empty registry."""
        self._providers: Dict[str, Type[BaseLLMProvider]] = {}
        self._provider_metadata: Dict[str, Dict] = {}

    def register(
        self,
        name: str,
        provider_class: Type[BaseLLMProvider],
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Register a new LLM provider.

        Args:
            name: Unique identifier for the provider (e.g., "gemini", "cohere")
            provider_class: Class implementing BaseLLMProvider
            metadata: Optional provider metadata (description, capabilities, etc.)

        Raises:
            ValueError: If provider name is already registered or class invalid

        Example:
            registry.register(
                "gemini",
                GeminiProvider,
                metadata={
                    "description": "Google Gemini Pro",
                    "supports_streaming": True,
                    "max_tokens": 32000
                }
            )
        """
        # Validate provider class
        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError(
                f"Provider class must inherit from BaseLLMProvider, "
                f"got {provider_class.__name__}"
            )

        # Check for duplicates
        if name in self._providers:
            logger.warning(
                f"Provider '{name}' already registered, overwriting with {provider_class.__name__}"
            )

        # Register provider
        self._providers[name] = provider_class
        self._provider_metadata[name] = metadata or {}

        logger.info(
            f"Registered provider: {name} ({provider_class.__name__})"
        )

    def unregister(self, name: str) -> None:
        """
        Unregister a provider.

        Args:
            name: Provider identifier to remove

        Raises:
            KeyError: If provider not found
        """
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' not registered")

        del self._providers[name]
        del self._provider_metadata[name]
        logger.info(f"Unregistered provider: {name}")

    def get(self, name: str) -> Type[BaseLLMProvider]:
        """
        Get provider class by name.

        Args:
            name: Provider identifier

        Returns:
            Provider class (not instance)

        Raises:
            KeyError: If provider not found

        Example:
            provider_class = registry.get("anthropic")
            provider = provider_class(config)
        """
        if name not in self._providers:
            available = ", ".join(self.list_providers())
            raise KeyError(
                f"Provider '{name}' not found. Available: {available}"
            )

        return self._providers[name]

    def get_metadata(self, name: str) -> Dict:
        """Get provider metadata."""
        return self._provider_metadata.get(name, {})

    def list_providers(self) -> List[str]:
        """Get list of all registered provider names."""
        return list(self._providers.keys())

    def is_registered(self, name: str) -> bool:
        """Check if a provider is registered."""
        return name in self._providers

    def create_provider(
        self,
        name: str,
        config: ProviderConfig
    ) -> BaseLLMProvider:
        """
        Convenience method to create a provider instance.

        Args:
            name: Provider identifier
            config: Provider configuration

        Returns:
            Initialized provider instance

        Example:
            config = ProviderConfig(api_key="sk-...")
            provider = registry.create_provider("anthropic", config)
        """
        provider_class = self.get(name)
        return provider_class(config)


# Global registry instance
_global_registry = None


def get_global_registry() -> ProviderRegistry:
    """
    Get the global provider registry singleton.

    Returns:
        Global ProviderRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ProviderRegistry()
        _register_builtin_providers(_global_registry)
    return _global_registry


def _register_builtin_providers(registry: ProviderRegistry) -> None:
    """Register built-in TrustChain providers."""
    from .anthropic_provider import AnthropicProvider
    from .openai_provider import OpenAIProvider
    from .llama_provider import LlamaProvider

    registry.register(
        "anthropic",
        AnthropicProvider,
        metadata={
            "description": "Anthropic Claude models",
            "models": ["claude-opus-4", "claude-sonnet-4", "claude-sonnet-3-5", "claude-haiku-3-5"],
            "supports_streaming": True,
            "max_tokens": 200000,
            "reasoning_quality": "excellent"
        }
    )

    registry.register(
        "openai",
        OpenAIProvider,
        metadata={
            "description": "OpenAI GPT models",
            "models": ["gpt-4", "gpt-4-turbo", "gpt-4o"],
            "supports_streaming": True,
            "max_tokens": 128000,
            "reasoning_quality": "excellent"
        }
    )

    registry.register(
        "llama",
        LlamaProvider,
        metadata={
            "description": "Local Llama models via Ollama",
            "models": ["llama3.1", "llama3.1:70b", "llama2"],
            "supports_streaming": True,
            "max_tokens": 8192,
            "reasoning_quality": "good",
            "local": True,
            "privacy": "high"
        }
    )


def register_provider(
    name: str,
    provider_class: Type[BaseLLMProvider],
    metadata: Optional[Dict] = None
) -> None:
    """
    Convenience function to register a provider with the global registry.

    Args:
        name: Unique provider identifier
        provider_class: Class implementing BaseLLMProvider
        metadata: Optional provider metadata

    Example:
        from my_custom_provider import GeminiProvider

        register_provider(
            "gemini",
            GeminiProvider,
            metadata={"description": "Google Gemini"}
        )
    """
    registry = get_global_registry()
    registry.register(name, provider_class, metadata)

"""
TrustChain LLM Provider System

This module provides a flexible, extensible architecture for integrating
multiple LLM providers into TrustChain's consensus decision-making system.

Architecture:
- BaseLLMProvider: Abstract interface all providers must implement
- ProviderRegistry: Dynamic registration and discovery system
- Built-in providers: Anthropic (Claude), OpenAI (GPT), Llama (local)
- Custom providers: Easy template for adding new LLMs

Usage:
    # Basic usage with built-in providers
    from providers import get_global_registry, ProviderConfig

    registry = get_global_registry()
    config = ProviderConfig(api_key="sk-...")

    claude = registry.create_provider("anthropic", config)
    gpt = registry.create_provider("openai", config)

    # Add custom provider
    from providers import register_provider
    from my_provider import GeminiProvider

    register_provider("gemini", GeminiProvider, metadata={...})
    gemini = registry.create_provider("gemini", config)

Commercial Use:
    TrustChain supports both government/non-profit (Apache 2.0) and
    commercial licensing. See LICENSE_COMMERCIAL.md for details.

Custom Providers:
    See custom_provider_template.py for a complete guide on adding
    support for new LLM providers like Gemini, Cohere, Mistral, etc.
"""

from .base import (
    BaseLLMProvider,
    LLMResponse,
    ModelProvider,
    ProviderConfig,
    ProviderStatus,
    ProviderException
)

from .registry import (
    ProviderRegistry,
    get_global_registry,
    register_provider
)

from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .llama_provider import LlamaProvider

__all__ = [
    # Base classes and types
    "BaseLLMProvider",
    "LLMResponse",
    "ModelProvider",
    "ProviderConfig",
    "ProviderStatus",
    "ProviderException",

    # Registry
    "ProviderRegistry",
    "get_global_registry",
    "register_provider",

    # Provider implementations
    "AnthropicProvider",
    "OpenAIProvider",
    "LlamaProvider",
]

__version__ = "1.1.0"
__author__ = "Kareem (Jack) Almac"
__license__ = "Apache 2.0 / Commercial (Dual License)"

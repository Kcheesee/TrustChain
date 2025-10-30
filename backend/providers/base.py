"""
Abstract base provider for LLM interactions in TrustChain.

This module defines the interface that all LLM providers must implement,
ensuring consistent behavior across different AI models while maintaining
government compliance requirements for audit trails and error handling.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import asyncio
from dataclasses import dataclass, field
import logging

# Configure logging for compliance and debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Enumeration of supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LLAMA = "llama"


class ProviderStatus(str, Enum):
    """Provider health status for monitoring."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class LLMResponse:
    """
    Structured response from an LLM provider.

    This standardized format ensures all provider responses can be
    consistently logged for FOIA compliance and analyzed for consensus.
    """
    provider: ModelProvider
    model_name: str
    content: str
    reasoning: Optional[str]
    confidence: Optional[float]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    def to_audit_dict(self) -> Dict[str, Any]:
        """
        Convert response to audit-safe dictionary.

        Returns sanitized data suitable for immutable audit logging,
        excluding potentially sensitive metadata while preserving
        decision-making context.
        """
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "content": self.content,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "error": self.error
        }


@dataclass
class ProviderConfig:
    """Configuration for LLM provider initialization."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: int = 60
    temperature: float = 0.7
    max_tokens: int = 2000

    # Government compliance settings
    enable_content_filtering: bool = True
    log_all_requests: bool = True
    pii_detection: bool = True


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    Implements the Template Method pattern to enforce consistent
    error handling, retry logic, and audit logging across all
    AI model integrations. Subclasses must implement model-specific
    communication while inheriting compliance safeguards.
    """

    def __init__(
        self,
        provider: ModelProvider,
        config: ProviderConfig
    ):
        """
        Initialize the provider with configuration.

        Args:
            provider: The type of provider (Anthropic, OpenAI, etc.)
            config: Configuration object with API keys and settings
        """
        self.provider = provider
        self.config = config
        self._status = ProviderStatus.HEALTHY
        self._request_count = 0
        self._error_count = 0

        logger.info(f"Initializing {provider.value} provider with config: {config}")

    @abstractmethod
    async def _make_api_call(
        self,
        prompt: str,
        system_context: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Make the actual API call to the LLM provider.

        This method must be implemented by each provider subclass
        to handle provider-specific API communication.

        Args:
            prompt: The user prompt/question
            system_context: System-level instructions (e.g., government policy context)
            **kwargs: Provider-specific additional parameters

        Returns:
            LLMResponse object with structured response data

        Raises:
            ProviderException: If the API call fails
        """
        pass

    @abstractmethod
    async def validate_api_key(self) -> bool:
        """
        Validate that the API key is functional.

        Returns:
            True if API key is valid and service is reachable
        """
        pass

    async def generate_decision(
        self,
        prompt: str,
        system_context: Optional[str] = None,
        decision_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a decision with automatic retry logic and audit logging.

        This is the main entry point for getting decisions from the LLM.
        It wraps the provider-specific API call with retry logic, error
        handling, and compliance logging required for government use.

        Args:
            prompt: The decision prompt (e.g., unemployment benefit application)
            system_context: Government policy context and requirements
            decision_context: Additional context for audit trail (case ID, etc.)
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with the decision and reasoning

        Raises:
            ProviderException: After all retries exhausted
        """
        start_time = datetime.now()
        decision_context = decision_context or {}

        # Log the request for compliance
        if self.config.log_all_requests:
            logger.info(
                f"Decision request to {self.provider.value} - "
                f"Context: {decision_context}"
            )

        # Implement exponential backoff retry logic
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                self._request_count += 1

                # Make the actual API call
                response = await asyncio.wait_for(
                    self._make_api_call(prompt, system_context, **kwargs),
                    timeout=self.config.timeout_seconds
                )

                # Calculate latency for monitoring
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                response.latency_ms = latency_ms

                # Log successful response
                logger.info(
                    f"Successful response from {self.provider.value} - "
                    f"Latency: {latency_ms}ms, Tokens: {response.tokens_used}"
                )

                return response

            except asyncio.TimeoutError as e:
                last_exception = e
                self._error_count += 1
                logger.warning(
                    f"Timeout on {self.provider.value} (attempt {attempt + 1}/{self.config.max_retries})"
                )

            except Exception as e:
                last_exception = e
                self._error_count += 1
                logger.error(
                    f"Error on {self.provider.value} (attempt {attempt + 1}/{self.config.max_retries}): {str(e)}"
                )

            # Exponential backoff before retry
            if attempt < self.config.max_retries - 1:
                backoff_seconds = 2 ** attempt
                logger.info(f"Retrying in {backoff_seconds} seconds...")
                await asyncio.sleep(backoff_seconds)

        # All retries exhausted - update status and raise
        self._update_status()
        error_response = LLMResponse(
            provider=self.provider,
            model_name="unknown",
            content="",
            reasoning=None,
            confidence=None,
            timestamp=datetime.now(),
            error=f"Failed after {self.config.max_retries} attempts: {str(last_exception)}"
        )

        logger.error(
            f"All retries exhausted for {self.provider.value}. "
            f"Total errors: {self._error_count}/{self._request_count}"
        )

        return error_response

    def _update_status(self) -> None:
        """
        Update provider health status based on error rate.

        This enables the orchestrator to route around unhealthy providers
        and maintain system reliability.
        """
        if self._request_count == 0:
            self._status = ProviderStatus.HEALTHY
            return

        error_rate = self._error_count / self._request_count

        if error_rate > 0.5:
            self._status = ProviderStatus.UNAVAILABLE
        elif error_rate > 0.2:
            self._status = ProviderStatus.DEGRADED
        else:
            self._status = ProviderStatus.HEALTHY

        logger.info(
            f"{self.provider.value} status: {self._status.value} "
            f"(error rate: {error_rate:.2%})"
        )

    def get_status(self) -> ProviderStatus:
        """Get current health status of the provider."""
        return self._status

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get provider performance metrics.

        Returns metrics for monitoring dashboards and compliance reporting.
        """
        error_rate = (
            self._error_count / self._request_count
            if self._request_count > 0
            else 0.0
        )

        return {
            "provider": self.provider.value,
            "status": self._status.value,
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate": error_rate,
            "health_score": max(0.0, 1.0 - error_rate)
        }


class ProviderException(Exception):
    """Base exception for provider errors."""

    def __init__(
        self,
        message: str,
        provider: ModelProvider,
        recoverable: bool = True
    ):
        """
        Initialize provider exception.

        Args:
            message: Error description
            provider: Which provider raised the error
            recoverable: Whether retry might succeed
        """
        self.message = message
        self.provider = provider
        self.recoverable = recoverable
        super().__init__(self.message)

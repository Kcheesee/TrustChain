"""
OpenAI GPT provider implementation for TrustChain.

Implements the OpenAI API integration with production-ready error handling,
response parsing, and government compliance features.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError

from .base import (
    BaseLLMProvider,
    LLMResponse,
    ModelProvider,
    ProviderConfig,
    ProviderException
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    Production-ready OpenAI GPT provider.

    Implements the OpenAI API with proper error handling, response parsing,
    and audit logging. Provides consensus diversity alongside Claude.
    """

    # Available GPT models
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4O = "gpt-4o"
    GPT_35_TURBO = "gpt-3.5-turbo"

    def __init__(
        self,
        config: ProviderConfig,
        model: str = GPT_4O
    ):
        """
        Initialize OpenAI provider.

        Args:
            config: Provider configuration with API key
            model: GPT model to use (defaults to GPT-4o for best performance)
        """
        super().__init__(ModelProvider.OPENAI, config)

        if not config.api_key:
            raise ProviderException(
                "OpenAI API key is required",
                ModelProvider.OPENAI,
                recoverable=False
            )

        self.model = model
        self.client = AsyncOpenAI(api_key=config.api_key)

        logger.info(f"OpenAI provider initialized with model: {model}")

    async def validate_api_key(self) -> bool:
        """
        Validate the OpenAI API key by making a minimal test request.

        Returns:
            True if API key is valid and service is reachable

        Raises:
            ProviderException: If API key is invalid
        """
        try:
            # Make a minimal request to validate credentials
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )

            logger.info("OpenAI API key validated successfully")
            return True

        except APIError as e:
            logger.error(f"OpenAI API key validation failed: {str(e)}")
            raise ProviderException(
                f"Invalid OpenAI API key: {str(e)}",
                ModelProvider.OPENAI,
                recoverable=False
            )

    async def _make_api_call(
        self,
        prompt: str,
        system_context: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Make API call to GPT with proper error handling.

        Args:
            prompt: The user prompt/question
            system_context: System-level instructions (government policy context)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with GPT's decision and reasoning

        Raises:
            ProviderException: If API call fails
        """
        start_time = datetime.now()

        try:
            # Build the messages array for GPT
            messages = []

            # Add system context if provided (critical for government decision-making)
            if system_context:
                messages.append({"role": "system", "content": system_context})

            messages.append({"role": "user", "content": prompt})

            # Prepare API parameters
            api_params = {
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "messages": messages
            }

            logger.debug(f"Making OpenAI API call with params: {api_params}")

            # Make the API call
            response = await self.client.chat.completions.create(**api_params)

            # Extract content from response
            content = response.choices[0].message.content or ""

            # Parse reasoning if present
            reasoning = self._extract_reasoning(content)

            # Calculate confidence based on response characteristics
            confidence = self._calculate_confidence(response, content)

            # Calculate tokens used for cost tracking and auditing
            tokens_used = (
                response.usage.prompt_tokens + response.usage.completion_tokens
                if response.usage else None
            )

            llm_response = LLMResponse(
                provider=ModelProvider.OPENAI,
                model_name=self.model,
                content=content,
                reasoning=reasoning,
                confidence=confidence,
                timestamp=datetime.now(),
                tokens_used=tokens_used,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "model_id": response.model
                }
            )

            logger.info(
                f"OpenAI API call successful - Tokens: {tokens_used}, "
                f"Confidence: {confidence:.2f}"
            )

            return llm_response

        except RateLimitError as e:
            logger.warning(f"OpenAI rate limit hit: {str(e)}")
            raise ProviderException(
                f"Rate limit exceeded: {str(e)}",
                ModelProvider.OPENAI,
                recoverable=True
            )

        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {str(e)}")
            raise ProviderException(
                f"Connection failed: {str(e)}",
                ModelProvider.OPENAI,
                recoverable=True
            )

        except APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise ProviderException(
                f"API error: {str(e)}",
                ModelProvider.OPENAI,
                recoverable=False
            )

        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {str(e)}")
            raise ProviderException(
                f"Unexpected error: {str(e)}",
                ModelProvider.OPENAI,
                recoverable=False
            )

    def _extract_reasoning(self, content: str) -> Optional[str]:
        """
        Extract reasoning/thinking process from GPT's response.

        GPT often structures responses with explicit reasoning sections.
        This extracts them for audit trail transparency.

        Args:
            content: The full response content

        Returns:
            Extracted reasoning or None if not found
        """
        # Look for common reasoning patterns GPT uses
        reasoning_markers = [
            "Let me analyze",
            "Based on my analysis",
            "Here's my reasoning:",
            "Step-by-step:",
            "Analysis:",
            "Reasoning:"
        ]

        for marker in reasoning_markers:
            if marker.lower() in content.lower():
                # Extract the reasoning section
                parts = content.split(marker, 1)
                if len(parts) > 1:
                    # Get text after marker until decision/conclusion
                    reasoning_text = parts[1].split("\n\n")[0]
                    return reasoning_text.strip()

        # If no explicit reasoning section, return first paragraph as implicit reasoning
        paragraphs = content.split("\n\n")
        if len(paragraphs) > 1:
            return paragraphs[0].strip()

        return None

    def _calculate_confidence(self, response: Any, content: str) -> float:
        """
        Calculate confidence score based on response characteristics.

        Uses heuristics like response length, finish reason, and language
        certainty markers to estimate decision confidence.

        Args:
            response: The OpenAI API response
            content: Extracted text content

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Start at neutral

        # Higher confidence if response completed naturally
        finish_reason = response.choices[0].finish_reason
        if finish_reason == "stop":
            confidence += 0.2
        elif finish_reason == "length":
            confidence -= 0.1  # Incomplete response reduces confidence

        # Analyze language for certainty markers
        certainty_markers = [
            "clearly", "definitely", "certainly", "without doubt",
            "conclusively", "unambiguous"
        ]
        uncertainty_markers = [
            "might", "possibly", "perhaps", "unclear", "uncertain",
            "difficult to determine", "depends on"
        ]

        content_lower = content.lower()

        # Boost confidence for certainty markers
        certainty_count = sum(1 for marker in certainty_markers if marker in content_lower)
        confidence += min(0.2, certainty_count * 0.05)

        # Reduce confidence for uncertainty markers
        uncertainty_count = sum(1 for marker in uncertainty_markers if marker in content_lower)
        confidence -= min(0.3, uncertainty_count * 0.1)

        # Ensure confidence stays in valid range
        return max(0.0, min(1.0, confidence))

    async def generate_structured_decision(
        self,
        prompt: str,
        system_context: str,
        decision_criteria: Dict[str, Any]
    ) -> LLMResponse:
        """
        Generate a structured government decision with explicit criteria evaluation.

        This method is specifically designed for government use cases where
        decisions must be evaluated against explicit policy criteria.

        Args:
            prompt: The case details (e.g., unemployment application)
            system_context: Government policy and legal requirements
            decision_criteria: Dictionary of criteria to evaluate (e.g., eligibility rules)

        Returns:
            LLMResponse with structured decision and per-criterion evaluation
        """
        # Build enhanced prompt with structured output requirements
        structured_prompt = f"""
{prompt}

Please evaluate this case against the following criteria and provide:
1. A decision (APPROVE/DENY/NEEDS_REVIEW)
2. Reasoning for each criterion
3. Overall confidence in the decision

Criteria to evaluate:
{self._format_criteria(decision_criteria)}

Provide your response in the following structure:
- Decision: [APPROVE/DENY/NEEDS_REVIEW]
- Reasoning: [Step-by-step analysis]
- Criterion Evaluations: [For each criterion]
- Confidence: [High/Medium/Low]
"""

        return await self.generate_decision(
            prompt=structured_prompt,
            system_context=system_context
        )

    def _format_criteria(self, criteria: Dict[str, Any]) -> str:
        """
        Format decision criteria for prompt inclusion.

        Args:
            criteria: Dictionary of evaluation criteria

        Returns:
            Formatted criteria string
        """
        formatted = []
        for key, value in criteria.items():
            formatted.append(f"- {key}: {value}")
        return "\n".join(formatted)

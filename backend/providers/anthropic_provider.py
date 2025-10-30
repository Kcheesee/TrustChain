"""
Anthropic Claude provider implementation for TrustChain.

Implements the Anthropic API integration with production-ready error handling,
response parsing, and government compliance features.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from anthropic import AsyncAnthropic, APIError, APIConnectionError, RateLimitError
from anthropic.types import Message

from .base import (
    BaseLLMProvider,
    LLMResponse,
    ModelProvider,
    ProviderConfig,
    ProviderException
)

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """
    Production-ready Anthropic Claude provider.

    Implements the Claude API with proper error handling, response parsing,
    and audit logging. Designed for government compliance with full
    reasoning extraction and decision traceability.
    """

    # Available Claude models (as of 2025)
    CLAUDE_OPUS = "claude-3-opus-20240229"
    CLAUDE_SONNET = "claude-sonnet-4-20250514"  # Latest Sonnet 4
    CLAUDE_SONNET_35 = "claude-3-5-sonnet-20241022"  # Sonnet 3.5
    CLAUDE_HAIKU = "claude-3-haiku-20240307"

    def __init__(
        self,
        config: ProviderConfig,
        model: str = CLAUDE_HAIKU  # Changed to Haiku - most accessible
    ):
        """
        Initialize Anthropic provider.

        Args:
            config: Provider configuration with API key
            model: Claude model to use (defaults to Opus for highest quality)
        """
        super().__init__(ModelProvider.ANTHROPIC, config)

        if not config.api_key:
            raise ProviderException(
                "Anthropic API key is required",
                ModelProvider.ANTHROPIC,
                recoverable=False
            )

        self.model = model
        self.client = AsyncAnthropic(api_key=config.api_key)

        logger.info(f"Anthropic provider initialized with model: {model}")

    async def validate_api_key(self) -> bool:
        """
        Validate the Anthropic API key by making a minimal test request.

        Returns:
            True if API key is valid and service is reachable

        Raises:
            ProviderException: If API key is invalid
        """
        try:
            # Make a minimal request to validate credentials
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )

            logger.info("Anthropic API key validated successfully")
            return True

        except APIError as e:
            logger.error(f"Anthropic API key validation failed: {str(e)}")
            raise ProviderException(
                f"Invalid Anthropic API key: {str(e)}",
                ModelProvider.ANTHROPIC,
                recoverable=False
            )

    async def _make_api_call(
        self,
        prompt: str,
        system_context: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Make API call to Claude with proper error handling.

        Args:
            prompt: The user prompt/question
            system_context: System-level instructions (government policy context)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with Claude's decision and reasoning

        Raises:
            ProviderException: If API call fails
        """
        start_time = datetime.now()

        try:
            # Build the messages array for Claude
            messages = [{"role": "user", "content": prompt}]

            # Prepare API parameters
            api_params = {
                "model": self.model,
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "messages": messages
            }

            # Add system context if provided (critical for government decision-making)
            if system_context:
                api_params["system"] = system_context

            logger.debug(f"Making Anthropic API call with params: {api_params}")

            # Make the API call
            response: Message = await self.client.messages.create(**api_params)

            # Extract content from response
            content = self._extract_content(response)

            # Parse reasoning if present (Claude often provides step-by-step thinking)
            reasoning = self._extract_reasoning(content)

            # Calculate confidence based on response characteristics
            confidence = self._calculate_confidence(response, content)

            # Calculate tokens used for cost tracking and auditing
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            llm_response = LLMResponse(
                provider=ModelProvider.ANTHROPIC,
                model_name=self.model,
                content=content,
                reasoning=reasoning,
                confidence=confidence,
                timestamp=datetime.now(),
                tokens_used=tokens_used,
                metadata={
                    "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "model_id": response.model
                }
            )

            logger.info(
                f"Claude API call successful - Tokens: {tokens_used}, "
                f"Confidence: {confidence:.2f}"
            )

            return llm_response

        except RateLimitError as e:
            logger.warning(f"Anthropic rate limit hit: {str(e)}")
            raise ProviderException(
                f"Rate limit exceeded: {str(e)}",
                ModelProvider.ANTHROPIC,
                recoverable=True
            )

        except APIConnectionError as e:
            logger.error(f"Anthropic connection error: {str(e)}")
            raise ProviderException(
                f"Connection failed: {str(e)}",
                ModelProvider.ANTHROPIC,
                recoverable=True
            )

        except APIError as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise ProviderException(
                f"API error: {str(e)}",
                ModelProvider.ANTHROPIC,
                recoverable=False
            )

        except Exception as e:
            logger.error(f"Unexpected error in Anthropic provider: {str(e)}")
            raise ProviderException(
                f"Unexpected error: {str(e)}",
                ModelProvider.ANTHROPIC,
                recoverable=False
            )

    def _extract_content(self, response: Message) -> str:
        """
        Extract text content from Claude response.

        Claude can return multiple content blocks; this combines them
        into a single string for consistent handling.

        Args:
            response: The Claude API response

        Returns:
            Combined text content
        """
        content_parts = []

        for block in response.content:
            if hasattr(block, 'text'):
                content_parts.append(block.text)

        return "\n".join(content_parts)

    def _extract_reasoning(self, content: str) -> Optional[str]:
        """
        Extract reasoning/thinking process from Claude's response.

        Claude often structures responses with explicit reasoning sections.
        This extracts them for audit trail transparency.

        Args:
            content: The full response content

        Returns:
            Extracted reasoning or None if not found
        """
        # Look for common reasoning patterns Claude uses
        reasoning_markers = [
            "Let me think through this",
            "Here's my reasoning:",
            "Step-by-step analysis:",
            "My analysis:",
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

    def _calculate_confidence(self, response: Message, content: str) -> float:
        """
        Calculate confidence score based on response characteristics.

        Uses heuristics like response length, stop reason, and language
        certainty markers to estimate decision confidence. Critical for
        identifying cases that need human review.

        Args:
            response: The Claude API response
            content: Extracted text content

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Start at neutral

        # Higher confidence if response completed naturally
        if response.stop_reason == "end_turn":
            confidence += 0.2
        elif response.stop_reason == "max_tokens":
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

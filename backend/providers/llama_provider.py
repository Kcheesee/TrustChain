"""
Llama/Ollama provider implementation for TrustChain.

Implements local Llama model integration via Ollama for privacy-sensitive
government decisions that require on-premises processing.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging
import json

import aiohttp

from .base import (
    BaseLLMProvider,
    LLMResponse,
    ModelProvider,
    ProviderConfig,
    ProviderException
)

logger = logging.getLogger(__name__)


class LlamaProvider(BaseLLMProvider):
    """
    Production-ready Llama provider via Ollama.

    Implements local LLM integration through Ollama's API. Critical for
    government use cases requiring on-premises processing for sensitive data
    that cannot be sent to external APIs.
    """

    # Available Llama models via Ollama
    LLAMA_2_7B = "llama2:7b"
    LLAMA_2_13B = "llama2:13b"
    LLAMA_2_70B = "llama2:70b"
    LLAMA_3_8B = "llama3:8b"
    LLAMA_3_70B = "llama3:70b"

    def __init__(
        self,
        config: ProviderConfig,
        model: str = LLAMA_2_13B,
        ollama_base_url: str = "http://localhost:11434"
    ):
        """
        Initialize Llama provider.

        Args:
            config: Provider configuration
            model: Llama model to use (defaults to 13B for balanced performance)
            ollama_base_url: Base URL for Ollama API (defaults to localhost)
        """
        super().__init__(ModelProvider.LLAMA, config)

        self.model = model
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.api_endpoint = f"{self.ollama_base_url}/api/generate"

        logger.info(
            f"Llama provider initialized with model: {model}, "
            f"Ollama URL: {ollama_base_url}"
        )

    async def validate_api_key(self) -> bool:
        """
        Validate that Ollama is running and accessible.

        Returns:
            True if Ollama is reachable and the model is available

        Raises:
            ProviderException: If Ollama is not accessible
        """
        try:
            # Check if Ollama is running
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m["name"] for m in data.get("models", [])]

                        if self.model not in models:
                            logger.warning(
                                f"Model {self.model} not found in Ollama. "
                                f"Available models: {models}"
                            )
                            # Don't fail validation - model might need to be pulled
                            logger.info(f"Ollama is accessible. Model {self.model} may need to be pulled.")

                        logger.info("Ollama validated successfully")
                        return True
                    else:
                        raise ProviderException(
                            f"Ollama returned status {response.status}",
                            ModelProvider.LLAMA,
                            recoverable=True
                        )

        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection failed: {str(e)}")
            raise ProviderException(
                f"Cannot connect to Ollama at {self.ollama_base_url}: {str(e)}",
                ModelProvider.LLAMA,
                recoverable=True
            )

    async def _make_api_call(
        self,
        prompt: str,
        system_context: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Make API call to Ollama with proper error handling.

        Args:
            prompt: The user prompt/question
            system_context: System-level instructions (government policy context)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with Llama's decision and reasoning

        Raises:
            ProviderException: If API call fails
        """
        start_time = datetime.now()

        try:
            # Build the full prompt with system context
            full_prompt = prompt
            if system_context:
                full_prompt = f"{system_context}\n\n{prompt}"

            # Prepare API parameters for Ollama
            api_params = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,  # Get complete response, not streaming
                "options": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "num_predict": kwargs.get("max_tokens", self.config.max_tokens)
                }
            }

            logger.debug(f"Making Ollama API call with model: {self.model}")

            # Make the API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_endpoint,
                    json=api_params,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ProviderException(
                            f"Ollama returned status {response.status}: {error_text}",
                            ModelProvider.LLAMA,
                            recoverable=True
                        )

                    data = await response.json()

            # Extract content from response
            content = data.get("response", "")

            # Parse reasoning if present
            reasoning = self._extract_reasoning(content)

            # Calculate confidence based on response characteristics
            confidence = self._calculate_confidence(data, content)

            # Estimate tokens used (Ollama doesn't always provide this)
            tokens_used = data.get("eval_count", None)

            llm_response = LLMResponse(
                provider=ModelProvider.LLAMA,
                model_name=self.model,
                content=content,
                reasoning=reasoning,
                confidence=confidence,
                timestamp=datetime.now(),
                tokens_used=tokens_used,
                metadata={
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "eval_count": data.get("eval_count"),
                    "context": data.get("context", [])
                }
            )

            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"Ollama API call successful - Latency: {latency_ms}ms, "
                f"Tokens: {tokens_used}, Confidence: {confidence:.2f}"
            )

            return llm_response

        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection error: {str(e)}")
            raise ProviderException(
                f"Connection failed: {str(e)}",
                ModelProvider.LLAMA,
                recoverable=True
            )

        except asyncio.TimeoutError as e:
            logger.error(f"Ollama request timeout: {str(e)}")
            raise ProviderException(
                f"Request timeout after {self.config.timeout_seconds}s",
                ModelProvider.LLAMA,
                recoverable=True
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Ollama: {str(e)}")
            raise ProviderException(
                f"Invalid response format: {str(e)}",
                ModelProvider.LLAMA,
                recoverable=False
            )

        except Exception as e:
            logger.error(f"Unexpected error in Llama provider: {str(e)}")
            raise ProviderException(
                f"Unexpected error: {str(e)}",
                ModelProvider.LLAMA,
                recoverable=False
            )

    def _extract_reasoning(self, content: str) -> Optional[str]:
        """
        Extract reasoning/thinking process from Llama's response.

        Args:
            content: The full response content

        Returns:
            Extracted reasoning or None if not found
        """
        # Look for common reasoning patterns
        reasoning_markers = [
            "Let me analyze",
            "Based on the information",
            "Here's my reasoning:",
            "Step by step:",
            "Analysis:",
            "Reasoning:"
        ]

        for marker in reasoning_markers:
            if marker.lower() in content.lower():
                # Extract the reasoning section
                parts = content.split(marker, 1)
                if len(parts) > 1:
                    reasoning_text = parts[1].split("\n\n")[0]
                    return reasoning_text.strip()

        # If no explicit reasoning section, return first paragraph
        paragraphs = content.split("\n\n")
        if len(paragraphs) > 1:
            return paragraphs[0].strip()

        return None

    def _calculate_confidence(self, response_data: Dict[str, Any], content: str) -> float:
        """
        Calculate confidence score based on response characteristics.

        For local models like Llama, we use different heuristics than
        commercial APIs since we don't get finish reasons.

        Args:
            response_data: The raw Ollama response data
            content: Extracted text content

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.5  # Start at neutral

        # Check if response completed fully (not truncated)
        eval_count = response_data.get("eval_count", 0)
        if eval_count > 0 and eval_count < self.config.max_tokens * 0.9:
            confidence += 0.1  # Response completed naturally

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

        # Local models generally have slightly lower confidence than commercial APIs
        confidence = confidence * 0.9

        # Ensure confidence stays in valid range
        return max(0.0, min(1.0, confidence))

    async def pull_model(self) -> bool:
        """
        Pull/download the Llama model if not already available.

        Returns:
            True if model was successfully pulled

        Raises:
            ProviderException: If model pull fails
        """
        try:
            logger.info(f"Attempting to pull model: {self.model}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_base_url}/api/pull",
                    json={"name": self.model, "stream": False},
                    timeout=aiohttp.ClientTimeout(total=600)  # 10 min timeout for large models
                ) as response:
                    if response.status == 200:
                        logger.info(f"Model {self.model} pulled successfully")
                        return True
                    else:
                        error_text = await response.text()
                        raise ProviderException(
                            f"Failed to pull model: {error_text}",
                            ModelProvider.LLAMA,
                            recoverable=False
                        )

        except Exception as e:
            logger.error(f"Error pulling model: {str(e)}")
            raise ProviderException(
                f"Model pull failed: {str(e)}",
                ModelProvider.LLAMA,
                recoverable=False
            )

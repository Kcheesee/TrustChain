"""
Enhanced bias detection with contextual analysis.

Adds sentiment-aware detection to distinguish between:
- Neutral mentions (e.g., "applicant is 25 years old" for verification)
- Discriminatory mentions (e.g., "applicant is too young at 25")
"""

import re
from typing import Dict, List, Tuple

# Sentiment indicators for bias detection
NEGATIVE_SENTIMENT_WORDS = {
    "too", "overly", "excessively", "inadequate", "insufficient",
    "problematic", "concerning", "risky", "questionable", "unsuitable",
    "unfit", "inappropriate", "unqualified", "lacking"
}

POSITIVE_SENTIMENT_WORDS = {
    "excellent", "strong", "qualified", "suitable", "appropriate",
    "capable", "competent", "experienced", "skilled"
}


def analyze_context(text: str, keyword: str) -> Tuple[bool, str]:
    """
    Analyze context around a protected attribute keyword.
    
    Args:
        text: Full text to analyze
        keyword: Protected attribute keyword found
        
    Returns:
        (is_discriminatory, context_snippet)
    """
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    
    # Find keyword position
    pos = text_lower.find(keyword_lower)
    if pos == -1:
        return False, ""
    
    # Extract context window (50 chars before/after)
    start = max(0, pos - 50)
    end = min(len(text), pos + len(keyword) + 50)
    context = text[start:end]
    
    # Check for negative sentiment around keyword
    context_words = set(context.lower().split())
    has_negative = bool(context_words & NEGATIVE_SENTIMENT_WORDS)
    has_positive = bool(context_words & POSITIVE_SENTIMENT_WORDS)
    
    # Patterns that suggest discrimination
    discriminatory_patterns = [
        r"too\s+(young|old)",
        r"because\s+of\s+(his|her|their)\s+(age|race|gender)",
        r"given\s+(his|her|their)\s+(background|ethnicity)",
        r"as\s+a\s+(woman|man|minority)",
        r"despite\s+being\s+(young|old|female|male)"
    ]
    
    is_discriminatory = any(
        re.search(pattern, context.lower())
        for pattern in discriminatory_patterns
    )
    
    # If negative sentiment + protected attribute = likely discriminatory
    if has_negative and not has_positive:
        is_discriminatory = True
    
    return is_discriminatory, context


def calculate_bias_severity(
    detected_attributes: List[str],
    discriminatory_contexts: int,
    total_mentions: int
) -> str:
    """
    Calculate severity of detected bias.
    
    Args:
        detected_attributes: List of protected attributes detected
        discriminatory_contexts: Number of discriminatory contexts
        total_mentions: Total protected attribute mentions
        
    Returns:
        Severity level: "low", "medium", "high", "critical"
    """
    if not detected_attributes:
        return "none"
    
    # Multiple protected attributes = higher severity
    if len(detected_attributes) >= 3:
        return "critical"
    
    # High ratio of discriminatory to total mentions
    if total_mentions > 0:
        discrimination_ratio = discriminatory_contexts / total_mentions
        if discrimination_ratio > 0.7:
            return "critical"
        elif discrimination_ratio > 0.4:
            return "high"
        elif discrimination_ratio > 0.2:
            return "medium"
    
    # Any discriminatory context is at least medium
    if discriminatory_contexts > 0:
        return "medium"
    
    # Mentions without discriminatory context = low
    return "low"

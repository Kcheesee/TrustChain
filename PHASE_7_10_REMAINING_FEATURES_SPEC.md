# TrustChain Phase 7-10: Remaining Features Spec

**Purpose**: Complete the TrustChain feature set with remaining analyzers, outputs, strategies, and testbed mode.

**Author**: Kareem Primo + Claude (November 2025)

---

## Overview

This document covers all remaining planned features for TrustChain v1.0:

| Phase | Feature | Type | Priority |
|-------|---------|------|----------|
| 7 | Gap Analysis | Analyzer | HIGH |
| 7 | Reasoning Quality Scoring | Analyzer | MEDIUM |
| 7 | Confidence Calibration | Analyzer | MEDIUM |
| 7 | Outcome Pattern Analysis | Analyzer | LOW |
| 8 | Training Signal | Output | MEDIUM |
| 8 | Appeal Package | Output | HIGH |
| 8 | Compliance Report | Output | HIGH |
| 9 | Constitutional Principles Check | Strategy | MEDIUM |
| 9 | Historical Consistency | Strategy | LOW |
| 10 | Testbed Mode | Feature | HIGH |

---

# PHASE 7: REMAINING ANALYZERS

---

## 7.1 Gap Analysis Analyzer

**Purpose**: Identify exactly which criteria were met, partially met, or missing. Powers the "here's what you're missing" feedback.

**File**: `backend/analyzers/gap_analysis.py`

### Data Models

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from core.base import BaseAnalyzer
from core.result import AnalysisResult


class CriteriaMatchLevel(str, Enum):
    """How well a criterion was matched."""
    EXCEEDED = "exceeded"      # Clearly above requirement
    MET = "met"                # Meets requirement
    PARTIAL = "partial"        # Some evidence but incomplete
    WEAK = "weak"              # Tangential evidence only
    MISSING = "missing"        # No evidence found


@dataclass
class CriterionMatch:
    """Match result for a single criterion."""
    
    # The criterion being evaluated
    criterion_id: str
    criterion_text: str
    criterion_category: str  # "required", "preferred", "nice_to_have"
    
    # Match assessment
    match_level: CriteriaMatchLevel
    confidence: float  # 0.0 - 1.0
    
    # Evidence
    evidence: List[str] = field(default_factory=list)  # Supporting text from input
    evidence_locations: List[str] = field(default_factory=list)  # Where found
    
    # Gap details (if not fully met)
    gap_description: Optional[str] = None
    suggestion: Optional[str] = None  # How to address the gap
    
    # Weighting
    weight: float = 1.0  # Importance of this criterion


@dataclass
class GapAnalysisResult:
    """Complete gap analysis output."""
    
    # Overall scores
    overall_match_score: float  # 0.0 - 1.0
    required_match_score: float  # Score for required criteria only
    
    # Breakdown
    criteria_matches: List[CriterionMatch] = field(default_factory=list)
    
    # Summary counts
    total_criteria: int = 0
    exceeded_count: int = 0
    met_count: int = 0
    partial_count: int = 0
    missing_count: int = 0
    
    # Critical gaps (required criteria not met)
    critical_gaps: List[CriterionMatch] = field(default_factory=list)
    
    # Improvement suggestions
    top_suggestions: List[str] = field(default_factory=list)
    
    # Keywords analysis
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
```

### Implementation

```python
class GapAnalysisAnalyzer(BaseAnalyzer):
    """
    Analyzes gaps between input/candidate and defined criteria.
    
    Works with criteria from:
    1. CriteriaDecomposition strategy output
    2. Explicitly provided criteria list
    3. Job posting requirements (for hiring use case)
    
    Usage:
        analyzer = GapAnalysisAnalyzer()
        result = await analyzer.analyze(
            input_data=candidate_data,
            criteria=job_requirements,  # Or from strategy result
            strategy_result=decomposition_result
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("gap_analysis", config)
        
        # Thresholds
        self.strong_match_threshold = 0.8
        self.partial_match_threshold = 0.5
        self.weak_match_threshold = 0.2
    
    async def analyze(
        self,
        input_data: Dict[str, Any],
        criteria: Optional[List[Dict[str, Any]]] = None,
        strategy_result: Optional[Any] = None,
        **kwargs
    ) -> AnalysisResult:
        """
        Run gap analysis.
        
        Args:
            input_data: The data being evaluated (resume, application, etc.)
            criteria: List of criteria dicts with {id, text, category, keywords, weight}
            strategy_result: Optional result from CriteriaDecomposition strategy
        """
        
        # Get criteria from strategy result if not provided
        if criteria is None and strategy_result:
            criteria = self._extract_criteria_from_strategy(strategy_result)
        
        if not criteria:
            return AnalysisResult(
                analyzer_name=self.name,
                passed=True,
                flags=[],
                warnings=["No criteria provided for gap analysis"],
                details={},
                recommendation="Unable to perform gap analysis without criteria"
            )
        
        # Analyze each criterion
        matches = []
        for crit in criteria:
            match = self._analyze_criterion(input_data, crit)
            matches.append(match)
        
        # Calculate scores
        gap_result = self._calculate_gap_result(matches)
        
        # Determine pass/fail
        # Fail if any required criteria are missing
        passed = len(gap_result.critical_gaps) == 0
        
        # Generate flags
        flags = []
        for gap in gap_result.critical_gaps:
            flags.append(
                f"Critical gap: '{gap.criterion_text}' - {gap.gap_description}"
            )
        
        # Warnings for partial matches on required
        warnings = []
        for match in matches:
            if match.criterion_category == "required" and match.match_level == CriteriaMatchLevel.PARTIAL:
                warnings.append(
                    f"Partial match on required criterion: '{match.criterion_text}'"
                )
        
        return AnalysisResult(
            analyzer_name=self.name,
            passed=passed,
            flags=flags,
            warnings=warnings,
            details={
                "overall_match_score": gap_result.overall_match_score,
                "required_match_score": gap_result.required_match_score,
                "total_criteria": gap_result.total_criteria,
                "exceeded": gap_result.exceeded_count,
                "met": gap_result.met_count,
                "partial": gap_result.partial_count,
                "missing": gap_result.missing_count,
                "critical_gaps": [
                    {"criterion": g.criterion_text, "gap": g.gap_description}
                    for g in gap_result.critical_gaps
                ],
                "top_suggestions": gap_result.top_suggestions,
                "matched_keywords": gap_result.matched_keywords,
                "missing_keywords": gap_result.missing_keywords,
                "criteria_breakdown": [
                    {
                        "criterion": m.criterion_text,
                        "category": m.criterion_category,
                        "match_level": m.match_level.value,
                        "confidence": m.confidence,
                        "evidence": m.evidence,
                        "suggestion": m.suggestion
                    }
                    for m in matches
                ]
            },
            recommendation=self._generate_recommendation(gap_result)
        )
    
    def _analyze_criterion(
        self, 
        input_data: Dict[str, Any], 
        criterion: Dict[str, Any]
    ) -> CriterionMatch:
        """Analyze how well input matches a single criterion."""
        
        crit_id = criterion.get("id", "unknown")
        crit_text = criterion.get("text", "")
        crit_category = criterion.get("category", "preferred")
        crit_keywords = criterion.get("keywords", [])
        crit_weight = criterion.get("weight", 1.0)
        
        # Flatten input data to searchable text
        input_text = self._flatten_input(input_data).lower()
        
        # Check keyword matches
        matched_kw = []
        missing_kw = []
        for kw in crit_keywords:
            if kw.lower() in input_text:
                matched_kw.append(kw)
            else:
                missing_kw.append(kw)
        
        # Calculate match ratio
        if crit_keywords:
            keyword_ratio = len(matched_kw) / len(crit_keywords)
        else:
            # No keywords defined - use fuzzy text matching
            keyword_ratio = self._fuzzy_match_criterion(input_text, crit_text)
        
        # Determine match level
        if keyword_ratio >= self.strong_match_threshold:
            match_level = CriteriaMatchLevel.EXCEEDED if keyword_ratio >= 0.95 else CriteriaMatchLevel.MET
        elif keyword_ratio >= self.partial_match_threshold:
            match_level = CriteriaMatchLevel.PARTIAL
        elif keyword_ratio >= self.weak_match_threshold:
            match_level = CriteriaMatchLevel.WEAK
        else:
            match_level = CriteriaMatchLevel.MISSING
        
        # Extract evidence
        evidence = self._extract_evidence(input_data, matched_kw)
        
        # Generate gap description and suggestion
        gap_desc = None
        suggestion = None
        if match_level in [CriteriaMatchLevel.MISSING, CriteriaMatchLevel.WEAK, CriteriaMatchLevel.PARTIAL]:
            gap_desc = f"Missing keywords: {', '.join(missing_kw)}" if missing_kw else "Insufficient evidence"
            suggestion = self._generate_suggestion(crit_text, missing_kw)
        
        return CriterionMatch(
            criterion_id=crit_id,
            criterion_text=crit_text,
            criterion_category=crit_category,
            match_level=match_level,
            confidence=keyword_ratio,
            evidence=evidence,
            gap_description=gap_desc,
            suggestion=suggestion,
            weight=crit_weight
        )
    
    def _flatten_input(self, input_data: Dict[str, Any]) -> str:
        """Flatten input dict to searchable text."""
        parts = []
        for key, value in input_data.items():
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict):
                        parts.extend(str(v) for v in item.values())
        return " ".join(parts)
    
    def _fuzzy_match_criterion(self, input_text: str, criterion_text: str) -> float:
        """Fuzzy match criterion against input when no keywords defined."""
        # Simple word overlap for now
        crit_words = set(criterion_text.lower().split())
        input_words = set(input_text.lower().split())
        
        # Remove common words
        stopwords = {"the", "a", "an", "in", "of", "to", "for", "and", "or", "with"}
        crit_words -= stopwords
        
        if not crit_words:
            return 0.5  # Can't evaluate
        
        overlap = len(crit_words & input_words)
        return overlap / len(crit_words)
    
    def _extract_evidence(
        self, 
        input_data: Dict[str, Any], 
        keywords: List[str]
    ) -> List[str]:
        """Extract sentences/bullets containing matched keywords."""
        evidence = []
        
        # Check common fields
        for field in ["resume_text", "experience", "skills", "summary"]:
            if field in input_data:
                value = input_data[field]
                if isinstance(value, str):
                    for kw in keywords:
                        if kw.lower() in value.lower():
                            # Extract surrounding context
                            evidence.append(f"Found '{kw}' in {field}")
                elif isinstance(value, list):
                    for item in value:
                        item_str = str(item)
                        for kw in keywords:
                            if kw.lower() in item_str.lower():
                                evidence.append(item_str[:100])
        
        return evidence[:5]  # Limit to 5 pieces of evidence
    
    def _generate_suggestion(
        self, 
        criterion_text: str, 
        missing_keywords: List[str]
    ) -> str:
        """Generate actionable suggestion for addressing a gap."""
        if missing_keywords:
            return f"Add experience demonstrating: {', '.join(missing_keywords[:3])}"
        return f"Add evidence for: {criterion_text}"
    
    def _calculate_gap_result(
        self, 
        matches: List[CriterionMatch]
    ) -> GapAnalysisResult:
        """Calculate overall gap analysis result."""
        
        # Count by match level
        exceeded = [m for m in matches if m.match_level == CriteriaMatchLevel.EXCEEDED]
        met = [m for m in matches if m.match_level == CriteriaMatchLevel.MET]
        partial = [m for m in matches if m.match_level == CriteriaMatchLevel.PARTIAL]
        weak = [m for m in matches if m.match_level == CriteriaMatchLevel.WEAK]
        missing = [m for m in matches if m.match_level == CriteriaMatchLevel.MISSING]
        
        # Calculate weighted scores
        total_weight = sum(m.weight for m in matches)
        if total_weight > 0:
            score_map = {
                CriteriaMatchLevel.EXCEEDED: 1.0,
                CriteriaMatchLevel.MET: 0.85,
                CriteriaMatchLevel.PARTIAL: 0.5,
                CriteriaMatchLevel.WEAK: 0.25,
                CriteriaMatchLevel.MISSING: 0.0
            }
            weighted_score = sum(
                score_map[m.match_level] * m.weight * m.confidence
                for m in matches
            ) / total_weight
        else:
            weighted_score = 0.0
        
        # Calculate required-only score
        required = [m for m in matches if m.criterion_category == "required"]
        if required:
            req_weight = sum(m.weight for m in required)
            req_score = sum(
                score_map[m.match_level] * m.weight * m.confidence
                for m in required
            ) / req_weight if req_weight > 0 else 0.0
        else:
            req_score = 1.0  # No required criteria
        
        # Identify critical gaps (required criteria not met)
        critical_gaps = [
            m for m in matches 
            if m.criterion_category == "required" 
            and m.match_level in [CriteriaMatchLevel.MISSING, CriteriaMatchLevel.WEAK]
        ]
        
        # Collect suggestions
        suggestions = [m.suggestion for m in matches if m.suggestion][:5]
        
        # Collect keywords
        all_matched = []
        all_missing = []
        for m in matches:
            if m.evidence:
                all_matched.extend([e.split("'")[1] for e in m.evidence if "'" in e])
        
        return GapAnalysisResult(
            overall_match_score=weighted_score,
            required_match_score=req_score,
            criteria_matches=matches,
            total_criteria=len(matches),
            exceeded_count=len(exceeded),
            met_count=len(met),
            partial_count=len(partial),
            missing_count=len(missing) + len(weak),
            critical_gaps=critical_gaps,
            top_suggestions=suggestions,
            matched_keywords=list(set(all_matched)),
            missing_keywords=list(set(all_missing))
        )
    
    def _generate_recommendation(self, result: GapAnalysisResult) -> str:
        """Generate human-readable recommendation."""
        if result.required_match_score >= 0.85 and len(result.critical_gaps) == 0:
            return f"STRONG FIT: Meets {result.met_count + result.exceeded_count}/{result.total_criteria} criteria. Proceed with confidence."
        
        if result.required_match_score >= 0.6 and len(result.critical_gaps) <= 1:
            return f"GOOD FIT: Minor gaps identified. Address: {result.top_suggestions[0] if result.top_suggestions else 'review partial matches'}"
        
        if len(result.critical_gaps) > 0:
            gap_list = ", ".join([g.criterion_text for g in result.critical_gaps[:2]])
            return f"GAPS FOUND: Critical missing requirements: {gap_list}. Consider addressing before proceeding."
        
        return f"MODERATE FIT: Score {result.overall_match_score:.0%}. Review suggestions for improvement."
    
    def _extract_criteria_from_strategy(self, strategy_result: Any) -> List[Dict[str, Any]]:
        """Extract criteria from a CriteriaDecomposition strategy result."""
        if hasattr(strategy_result, "criteria_scores"):
            return [
                {
                    "id": f"crit_{i}",
                    "text": crit.get("criterion", ""),
                    "category": crit.get("category", "preferred"),
                    "keywords": crit.get("keywords", []),
                    "weight": crit.get("weight", 1.0)
                }
                for i, crit in enumerate(strategy_result.criteria_scores)
            ]
        return []
```

### Tests for Gap Analysis

```python
# tests/test_gap_analysis.py

import pytest
from analyzers.gap_analysis import GapAnalysisAnalyzer, CriteriaMatchLevel


@pytest.fixture
def analyzer():
    return GapAnalysisAnalyzer()


@pytest.fixture
def sample_criteria():
    return [
        {
            "id": "python",
            "text": "Python programming experience",
            "category": "required",
            "keywords": ["python", "fastapi", "flask"],
            "weight": 2.0
        },
        {
            "id": "cloud",
            "text": "Cloud platform experience",
            "category": "required", 
            "keywords": ["aws", "azure", "gcp"],
            "weight": 1.5
        },
        {
            "id": "ml",
            "text": "Machine learning experience",
            "category": "preferred",
            "keywords": ["machine learning", "ml", "tensorflow", "pytorch"],
            "weight": 1.0
        }
    ]


@pytest.mark.asyncio
async def test_full_match(analyzer, sample_criteria):
    """Test input that matches all criteria."""
    input_data = {
        "skills": ["Python", "FastAPI", "AWS", "Machine Learning", "PyTorch"],
        "resume_text": "Experienced in Python, FastAPI, Flask, AWS, and ML projects."
    }
    
    result = await analyzer.analyze(input_data, criteria=sample_criteria)
    
    assert result.passed == True
    assert result.details["overall_match_score"] >= 0.8
    assert result.details["missing"] == 0


@pytest.mark.asyncio
async def test_critical_gap(analyzer, sample_criteria):
    """Test input missing required criteria."""
    input_data = {
        "skills": ["Java", "Spring Boot"],
        "resume_text": "Experienced Java developer with Spring Boot."
    }
    
    result = await analyzer.analyze(input_data, criteria=sample_criteria)
    
    assert result.passed == False
    assert len(result.flags) > 0
    assert "Critical gap" in result.flags[0]


@pytest.mark.asyncio
async def test_partial_match(analyzer, sample_criteria):
    """Test partial keyword matches."""
    input_data = {
        "skills": ["Python"],  # Has Python but not FastAPI/Flask
        "resume_text": "Python developer"
    }
    
    result = await analyzer.analyze(input_data, criteria=sample_criteria)
    
    # Should have partial match on Python criterion
    python_match = next(
        c for c in result.details["criteria_breakdown"] 
        if "Python" in c["criterion"]
    )
    assert python_match["match_level"] in ["partial", "met"]


@pytest.mark.asyncio
async def test_suggestions_generated(analyzer, sample_criteria):
    """Test that suggestions are generated for gaps."""
    input_data = {
        "skills": ["Python"],
        "resume_text": "Python developer"
    }
    
    result = await analyzer.analyze(input_data, criteria=sample_criteria)
    
    assert len(result.details["top_suggestions"]) > 0
```

---

## 7.2 Reasoning Quality Scoring Analyzer

**Purpose**: Assess how well the AI explained its decision. Vague reasoning = low confidence. Detailed, specific reasoning = high confidence.

**File**: `backend/analyzers/reasoning_quality.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

from core.base import BaseAnalyzer
from core.result import AnalysisResult


class ReasoningQuality(str, Enum):
    """Quality levels for reasoning."""
    EXCELLENT = "excellent"    # Specific, detailed, references evidence
    GOOD = "good"              # Clear reasoning with some specifics
    ADEQUATE = "adequate"      # Basic reasoning, could be more detailed
    POOR = "poor"              # Vague, generic, or circular
    MISSING = "missing"        # No reasoning provided


@dataclass
class ReasoningAssessment:
    """Assessment of reasoning quality."""
    
    quality: ReasoningQuality
    score: float  # 0.0 - 1.0
    
    # Breakdown
    specificity_score: float = 0.0      # Does it reference specific evidence?
    completeness_score: float = 0.0     # Does it address all criteria?
    coherence_score: float = 0.0        # Is the logic sound?
    evidence_score: float = 0.0         # Does it cite evidence?
    
    # Issues found
    issues: List[str] = field(default_factory=list)
    
    # Recommendations
    improvement_suggestions: List[str] = field(default_factory=list)


class ReasoningQualityAnalyzer(BaseAnalyzer):
    """
    Analyzes the quality of AI-generated reasoning.
    
    Checks for:
    - Specificity (vs vague statements)
    - Evidence citation
    - Logical coherence
    - Completeness
    - Absence of red flags (circular reasoning, contradictions)
    
    Usage:
        analyzer = ReasoningQualityAnalyzer()
        result = await analyzer.analyze(
            reasoning_text=model_output.reasoning,
            criteria=evaluated_criteria
        )
    """
    
    # Red flag patterns
    VAGUE_PATTERNS = [
        "seems like", "probably", "might be", "could be",
        "generally", "overall", "in general", "basically",
        "sort of", "kind of", "more or less"
    ]
    
    CIRCULAR_PATTERNS = [
        "because it is", "due to the fact that it is",
        "since they are", "as it is"
    ]
    
    HEDGE_PATTERNS = [
        "i think", "i believe", "in my opinion",
        "it appears", "it seems"
    ]
    
    STRONG_EVIDENCE_PATTERNS = [
        "specifically", "for example", "demonstrated by",
        "evidenced by", "shown in", "according to",
        "based on", "as stated in", "the candidate"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("reasoning_quality", config)
        
        self.min_quality_threshold = config.get("min_quality", 0.5) if config else 0.5
    
    async def analyze(
        self,
        reasoning_text: str = "",
        criteria: Optional[List[str]] = None,
        strategy_result: Optional[Any] = None,
        **kwargs
    ) -> AnalysisResult:
        """
        Analyze reasoning quality.
        
        Args:
            reasoning_text: The AI's reasoning/explanation
            criteria: List of criteria that should be addressed
            strategy_result: Optional strategy result containing reasoning
        """
        
        # Extract reasoning from strategy result if not provided
        if not reasoning_text and strategy_result:
            reasoning_text = getattr(strategy_result, "reasoning", "")
        
        if not reasoning_text:
            return AnalysisResult(
                analyzer_name=self.name,
                passed=False,
                flags=["No reasoning provided"],
                warnings=[],
                details={"quality": "missing", "score": 0.0},
                recommendation="Decision lacks explanation. Cannot assess reasoning quality."
            )
        
        # Assess reasoning
        assessment = self._assess_reasoning(reasoning_text, criteria or [])
        
        # Determine pass/fail
        passed = assessment.score >= self.min_quality_threshold
        
        # Generate flags and warnings
        flags = []
        warnings = []
        
        if assessment.quality == ReasoningQuality.POOR:
            flags.append("Reasoning quality is poor - decision may not be defensible")
        
        for issue in assessment.issues:
            if "circular" in issue.lower() or "vague" in issue.lower():
                flags.append(issue)
            else:
                warnings.append(issue)
        
        return AnalysisResult(
            analyzer_name=self.name,
            passed=passed,
            flags=flags,
            warnings=warnings,
            details={
                "quality": assessment.quality.value,
                "score": assessment.score,
                "specificity_score": assessment.specificity_score,
                "completeness_score": assessment.completeness_score,
                "coherence_score": assessment.coherence_score,
                "evidence_score": assessment.evidence_score,
                "issues": assessment.issues,
                "improvement_suggestions": assessment.improvement_suggestions
            },
            recommendation=self._generate_recommendation(assessment)
        )
    
    def _assess_reasoning(
        self, 
        reasoning: str, 
        criteria: List[str]
    ) -> ReasoningAssessment:
        """Assess reasoning quality across multiple dimensions."""
        
        reasoning_lower = reasoning.lower()
        
        # 1. Specificity score
        specificity = self._score_specificity(reasoning_lower)
        
        # 2. Evidence score
        evidence = self._score_evidence(reasoning_lower)
        
        # 3. Completeness score (does it address criteria?)
        completeness = self._score_completeness(reasoning_lower, criteria)
        
        # 4. Coherence score
        coherence = self._score_coherence(reasoning_lower)
        
        # Calculate overall score
        overall = (
            specificity * 0.3 +
            evidence * 0.3 +
            completeness * 0.2 +
            coherence * 0.2
        )
        
        # Determine quality level
        if overall >= 0.8:
            quality = ReasoningQuality.EXCELLENT
        elif overall >= 0.6:
            quality = ReasoningQuality.GOOD
        elif overall >= 0.4:
            quality = ReasoningQuality.ADEQUATE
        else:
            quality = ReasoningQuality.POOR
        
        # Identify issues
        issues = self._identify_issues(reasoning_lower)
        
        # Generate suggestions
        suggestions = self._generate_improvement_suggestions(
            specificity, evidence, completeness, coherence
        )
        
        return ReasoningAssessment(
            quality=quality,
            score=overall,
            specificity_score=specificity,
            completeness_score=completeness,
            coherence_score=coherence,
            evidence_score=evidence,
            issues=issues,
            improvement_suggestions=suggestions
        )
    
    def _score_specificity(self, text: str) -> float:
        """Score how specific the reasoning is."""
        score = 0.5  # Base score
        
        # Penalize vague language
        vague_count = sum(1 for p in self.VAGUE_PATTERNS if p in text)
        score -= vague_count * 0.1
        
        # Reward specific language
        specific_indicators = ["specifically", "exactly", "precisely", "in particular"]
        specific_count = sum(1 for p in specific_indicators if p in text)
        score += specific_count * 0.15
        
        # Reward numbers/metrics
        import re
        numbers = re.findall(r'\d+', text)
        score += min(len(numbers) * 0.05, 0.2)
        
        # Reward named entities (proper nouns suggest specific references)
        # Simple heuristic: words starting with capital mid-sentence
        sentences = text.split('.')
        for sent in sentences:
            words = sent.split()
            for i, word in enumerate(words[1:], 1):
                if word and word[0].isupper():
                    score += 0.02
        
        return max(0.0, min(1.0, score))
    
    def _score_evidence(self, text: str) -> float:
        """Score how well reasoning cites evidence."""
        score = 0.3  # Base score
        
        # Check for evidence patterns
        evidence_count = sum(1 for p in self.STRONG_EVIDENCE_PATTERNS if p in text)
        score += evidence_count * 0.15
        
        # Check for quotations or references
        if '"' in text or "'" in text:
            score += 0.1
        
        # Penalize hedging
        hedge_count = sum(1 for p in self.HEDGE_PATTERNS if p in text)
        score -= hedge_count * 0.1
        
        return max(0.0, min(1.0, score))
    
    def _score_completeness(self, text: str, criteria: List[str]) -> float:
        """Score how completely the reasoning addresses criteria."""
        if not criteria:
            return 0.7  # Can't evaluate without criteria
        
        # Check which criteria are mentioned
        addressed = 0
        for crit in criteria:
            # Extract key words from criterion
            key_words = [w.lower() for w in crit.split() if len(w) > 3]
            if any(kw in text for kw in key_words):
                addressed += 1
        
        return addressed / len(criteria) if criteria else 0.5
    
    def _score_coherence(self, text: str) -> float:
        """Score logical coherence of reasoning."""
        score = 0.7  # Base score
        
        # Penalize circular reasoning
        circular_count = sum(1 for p in self.CIRCULAR_PATTERNS if p in text)
        score -= circular_count * 0.2
        
        # Check for logical connectors
        logical_connectors = ["therefore", "because", "since", "thus", "consequently", "as a result"]
        connector_count = sum(1 for c in logical_connectors if c in text)
        score += min(connector_count * 0.1, 0.3)
        
        # Penalize contradictions (simple heuristic)
        contradiction_pairs = [
            ("is", "is not"), ("has", "lacks"), ("meets", "does not meet"),
            ("strong", "weak"), ("qualified", "unqualified")
        ]
        for pos, neg in contradiction_pairs:
            if pos in text and neg in text:
                score -= 0.15
        
        return max(0.0, min(1.0, score))
    
    def _identify_issues(self, text: str) -> List[str]:
        """Identify specific issues in reasoning."""
        issues = []
        
        # Check for vague language
        vague_found = [p for p in self.VAGUE_PATTERNS if p in text]
        if len(vague_found) >= 2:
            issues.append(f"Vague language detected: {', '.join(vague_found[:3])}")
        
        # Check for circular reasoning
        circular_found = [p for p in self.CIRCULAR_PATTERNS if p in text]
        if circular_found:
            issues.append("Potential circular reasoning detected")
        
        # Check for excessive hedging
        hedge_found = [p for p in self.HEDGE_PATTERNS if p in text]
        if len(hedge_found) >= 2:
            issues.append(f"Excessive hedging: {', '.join(hedge_found[:3])}")
        
        # Check length
        word_count = len(text.split())
        if word_count < 20:
            issues.append("Reasoning is too brief to be thorough")
        
        return issues
    
    def _generate_improvement_suggestions(
        self,
        specificity: float,
        evidence: float,
        completeness: float,
        coherence: float
    ) -> List[str]:
        """Generate suggestions for improving reasoning."""
        suggestions = []
        
        if specificity < 0.5:
            suggestions.append("Add specific examples and concrete details")
        
        if evidence < 0.5:
            suggestions.append("Cite specific evidence from the input to support conclusions")
        
        if completeness < 0.5:
            suggestions.append("Address all evaluation criteria explicitly")
        
        if coherence < 0.5:
            suggestions.append("Improve logical flow with clear cause-effect relationships")
        
        return suggestions
    
    def _generate_recommendation(self, assessment: ReasoningAssessment) -> str:
        """Generate overall recommendation."""
        if assessment.quality == ReasoningQuality.EXCELLENT:
            return "Reasoning is detailed and well-supported. Decision is defensible."
        
        if assessment.quality == ReasoningQuality.GOOD:
            return "Reasoning is adequate. Minor improvements would strengthen defensibility."
        
        if assessment.quality == ReasoningQuality.ADEQUATE:
            return f"Reasoning needs improvement: {assessment.improvement_suggestions[0] if assessment.improvement_suggestions else 'Add more detail'}"
        
        return f"Reasoning is poor and may not be defensible. Issues: {', '.join(assessment.issues[:2])}"
```

---

## 7.3 Confidence Calibration Analyzer

**Purpose**: Check if model confidence matches actual accuracy. If model says 90% confident but is only right 70% of the time, flag it.

**File**: `backend/analyzers/confidence_calibration.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from core.base import BaseAnalyzer
from core.result import AnalysisResult
from feedback.storage import FeedbackStore


@dataclass
class CalibrationBucket:
    """Calibration data for a confidence range."""
    range_start: float
    range_end: float
    predicted_count: int = 0
    actual_correct: int = 0
    
    @property
    def actual_accuracy(self) -> float:
        return self.actual_correct / self.predicted_count if self.predicted_count > 0 else 0.0
    
    @property
    def expected_accuracy(self) -> float:
        return (self.range_start + self.range_end) / 2
    
    @property
    def calibration_error(self) -> float:
        return abs(self.actual_accuracy - self.expected_accuracy)


@dataclass
class CalibrationAssessment:
    """Overall calibration assessment."""
    
    is_calibrated: bool
    calibration_error: float  # Mean absolute error
    
    # Direction of miscalibration
    is_overconfident: bool = False
    is_underconfident: bool = False
    
    # Bucket breakdown
    buckets: List[CalibrationBucket] = field(default_factory=list)
    
    # Current decision context
    current_confidence: float = 0.0
    adjusted_confidence: float = 0.0
    
    # Recommendations
    adjustment_applied: bool = False
    recommendation: str = ""


class ConfidenceCalibrationAnalyzer(BaseAnalyzer):
    """
    Analyzes whether model confidence scores are well-calibrated.
    
    Uses historical feedback data to:
    1. Build calibration curves
    2. Detect over/under-confidence
    3. Suggest adjusted confidence for current decision
    
    Usage:
        analyzer = ConfidenceCalibrationAnalyzer(feedback_store)
        result = await analyzer.analyze(
            current_confidence=0.85,
            model_name="claude",
            decision_type="hiring"
        )
    """
    
    def __init__(
        self, 
        feedback_store: Optional[FeedbackStore] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("confidence_calibration", config)
        self.feedback_store = feedback_store
        
        # Calibration thresholds
        self.calibration_threshold = 0.1  # Max acceptable error
        self.min_samples_per_bucket = 10
        
        # Bucket ranges
        self.bucket_ranges = [
            (0.0, 0.2), (0.2, 0.4), (0.4, 0.6), 
            (0.6, 0.8), (0.8, 0.9), (0.9, 1.0)
        ]
    
    async def analyze(
        self,
        current_confidence: float = 0.0,
        model_name: Optional[str] = None,
        decision_type: Optional[str] = None,
        strategy_result: Optional[Any] = None,
        **kwargs
    ) -> AnalysisResult:
        """
        Analyze confidence calibration.
        
        Args:
            current_confidence: Confidence of current decision
            model_name: Which model to check calibration for
            decision_type: Type of decision (for type-specific calibration)
            strategy_result: Strategy result containing confidence
        """
        
        # Extract confidence from strategy result if not provided
        if current_confidence == 0.0 and strategy_result:
            current_confidence = getattr(strategy_result, "confidence", 0.0)
        
        if not self.feedback_store:
            return AnalysisResult(
                analyzer_name=self.name,
                passed=True,
                flags=[],
                warnings=["No feedback store configured - cannot assess calibration"],
                details={"calibration_available": False},
                recommendation="Configure feedback store to enable calibration analysis"
            )
        
        # Build calibration curve from historical data
        assessment = await self._assess_calibration(
            current_confidence, model_name, decision_type
        )
        
        # Determine pass/fail
        passed = assessment.is_calibrated or not assessment.adjustment_applied
        
        # Generate flags and warnings
        flags = []
        warnings = []
        
        if assessment.is_overconfident:
            warnings.append(
                f"Model tends to be overconfident. "
                f"Reported {current_confidence:.0%} but historical accuracy is lower."
            )
        elif assessment.is_underconfident:
            warnings.append(
                f"Model tends to be underconfident. "
                f"Consider that actual accuracy may be higher than {current_confidence:.0%}."
            )
        
        if assessment.calibration_error > 0.2:
            flags.append(
                f"Severe calibration error ({assessment.calibration_error:.0%}). "
                f"Confidence scores may be unreliable."
            )
        
        return AnalysisResult(
            analyzer_name=self.name,
            passed=passed,
            flags=flags,
            warnings=warnings,
            details={
                "is_calibrated": assessment.is_calibrated,
                "calibration_error": assessment.calibration_error,
                "is_overconfident": assessment.is_overconfident,
                "is_underconfident": assessment.is_underconfident,
                "current_confidence": current_confidence,
                "adjusted_confidence": assessment.adjusted_confidence,
                "adjustment_applied": assessment.adjustment_applied,
                "bucket_data": [
                    {
                        "range": f"{b.range_start:.1f}-{b.range_end:.1f}",
                        "count": b.predicted_count,
                        "actual_accuracy": b.actual_accuracy,
                        "expected_accuracy": b.expected_accuracy,
                        "error": b.calibration_error
                    }
                    for b in assessment.buckets
                ]
            },
            recommendation=assessment.recommendation
        )
    
    async def _assess_calibration(
        self,
        current_confidence: float,
        model_name: Optional[str],
        decision_type: Optional[str]
    ) -> CalibrationAssessment:
        """Build calibration assessment from historical data."""
        
        # Get historical feedback
        feedback = await self.feedback_store.get_feedback_batch(
            start_date=datetime.now() - timedelta(days=90),
            decision_type=decision_type,
            limit=1000
        )
        
        if len(feedback) < 50:
            return CalibrationAssessment(
                is_calibrated=True,  # Assume calibrated if not enough data
                calibration_error=0.0,
                current_confidence=current_confidence,
                adjusted_confidence=current_confidence,
                recommendation="Insufficient historical data for calibration analysis"
            )
        
        # Build buckets
        buckets = [
            CalibrationBucket(range_start=start, range_end=end)
            for start, end in self.bucket_ranges
        ]
        
        # Populate buckets with feedback data
        for fb in feedback:
            # Get original confidence (would need to be stored with feedback)
            orig_confidence = getattr(fb, "original_confidence", 0.5)
            was_correct = fb.action.value.startswith("agree")
            
            # Find bucket
            for bucket in buckets:
                if bucket.range_start <= orig_confidence < bucket.range_end:
                    bucket.predicted_count += 1
                    if was_correct:
                        bucket.actual_correct += 1
                    break
        
        # Calculate calibration error
        valid_buckets = [b for b in buckets if b.predicted_count >= self.min_samples_per_bucket]
        if valid_buckets:
            calibration_error = sum(b.calibration_error for b in valid_buckets) / len(valid_buckets)
        else:
            calibration_error = 0.0
        
        # Determine over/under confidence
        total_expected = sum(b.expected_accuracy * b.predicted_count for b in valid_buckets)
        total_actual = sum(b.actual_correct for b in valid_buckets)
        total_count = sum(b.predicted_count for b in valid_buckets)
        
        if total_count > 0:
            avg_expected = total_expected / total_count
            avg_actual = total_actual / total_count
            is_overconfident = avg_expected > avg_actual + 0.05
            is_underconfident = avg_actual > avg_expected + 0.05
        else:
            is_overconfident = False
            is_underconfident = False
        
        # Calculate adjusted confidence
        adjusted_confidence = current_confidence
        adjustment_applied = False
        
        if calibration_error > self.calibration_threshold:
            # Find the bucket for current confidence
            for bucket in valid_buckets:
                if bucket.range_start <= current_confidence < bucket.range_end:
                    if bucket.predicted_count >= self.min_samples_per_bucket:
                        adjusted_confidence = bucket.actual_accuracy
                        adjustment_applied = True
                    break
        
        # Generate recommendation
        if calibration_error <= self.calibration_threshold:
            recommendation = "Model is well-calibrated. Confidence scores are reliable."
        elif is_overconfident:
            recommendation = f"Model is overconfident. Consider adjusted confidence of {adjusted_confidence:.0%} instead of {current_confidence:.0%}."
        elif is_underconfident:
            recommendation = f"Model is underconfident. Actual accuracy likely higher than reported {current_confidence:.0%}."
        else:
            recommendation = f"Calibration error of {calibration_error:.0%}. Review confidence scores with caution."
        
        return CalibrationAssessment(
            is_calibrated=calibration_error <= self.calibration_threshold,
            calibration_error=calibration_error,
            is_overconfident=is_overconfident,
            is_underconfident=is_underconfident,
            buckets=buckets,
            current_confidence=current_confidence,
            adjusted_confidence=adjusted_confidence,
            adjustment_applied=adjustment_applied,
            recommendation=recommendation
        )
```

---

## 7.4 Outcome Pattern Analysis Analyzer

**Purpose**: Detect statistical disparities over time. "Women are rejected 30% more often than men with similar qualifications."

**File**: `backend/analyzers/outcome_patterns.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics

from core.base import BaseAnalyzer
from core.result import AnalysisResult
from feedback.storage import FeedbackStore


class DisparityLevel(str, Enum):
    """Level of statistical disparity."""
    NONE = "none"           # Within acceptable bounds
    MINOR = "minor"         # Small but notable difference
    SIGNIFICANT = "significant"  # Clear disparity
    SEVERE = "severe"       # Major disparity requiring action


@dataclass
class GroupOutcome:
    """Outcome statistics for a demographic group."""
    group_name: str
    total_decisions: int = 0
    approvals: int = 0
    denials: int = 0
    needs_review: int = 0
    
    @property
    def approval_rate(self) -> float:
        return self.approvals / self.total_decisions if self.total_decisions > 0 else 0.0
    
    @property
    def denial_rate(self) -> float:
        return self.denials / self.total_decisions if self.total_decisions > 0 else 0.0


@dataclass
class DisparityReport:
    """Report on disparity between groups."""
    
    attribute: str  # "gender", "race_proxy", "location", etc.
    groups: List[GroupOutcome] = field(default_factory=list)
    
    # Disparity metrics
    disparity_level: DisparityLevel = DisparityLevel.NONE
    disparity_ratio: float = 1.0  # 1.0 = no disparity
    
    # Statistical significance
    sample_size_sufficient: bool = False
    p_value: Optional[float] = None
    
    # Details
    highest_approval_group: str = ""
    lowest_approval_group: str = ""
    
    # Recommendation
    recommendation: str = ""


class OutcomePatternAnalyzer(BaseAnalyzer):
    """
    Analyzes patterns in decision outcomes across demographic groups.
    
    Detects:
    - Approval rate disparities by group
    - Trends over time
    - Statistical significance of differences
    
    Usage:
        analyzer = OutcomePatternAnalyzer(feedback_store)
        result = await analyzer.analyze(
            decision_type="hiring",
            lookback_days=90
        )
    """
    
    def __init__(
        self,
        feedback_store: Optional[FeedbackStore] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("outcome_patterns", config)
        self.feedback_store = feedback_store
        
        # Disparity thresholds (using 80% rule common in employment law)
        self.minor_threshold = 0.9     # 90% of majority rate
        self.significant_threshold = 0.8  # 80% rule
        self.severe_threshold = 0.6
        
        self.min_group_size = 20
    
    async def analyze(
        self,
        decision_type: Optional[str] = None,
        lookback_days: int = 90,
        attributes_to_check: Optional[List[str]] = None,
        **kwargs
    ) -> AnalysisResult:
        """
        Analyze outcome patterns.
        
        Args:
            decision_type: Type of decisions to analyze
            lookback_days: How far back to look
            attributes_to_check: Which attributes to check for disparity
        """
        
        if not self.feedback_store:
            return AnalysisResult(
                analyzer_name=self.name,
                passed=True,
                flags=[],
                warnings=["No feedback store - cannot analyze patterns"],
                details={},
                recommendation="Configure feedback store to enable pattern analysis"
            )
        
        # Default attributes to check
        if attributes_to_check is None:
            attributes_to_check = ["gender", "race_proxy", "location", "university_tier"]
        
        # Get historical decisions
        decisions = await self._get_historical_decisions(
            decision_type, lookback_days
        )
        
        if len(decisions) < 50:
            return AnalysisResult(
                analyzer_name=self.name,
                passed=True,
                flags=[],
                warnings=["Insufficient data for pattern analysis"],
                details={"decision_count": len(decisions)},
                recommendation="Accumulate more decisions before pattern analysis is meaningful"
            )
        
        # Analyze each attribute
        disparity_reports = []
        for attr in attributes_to_check:
            report = self._analyze_attribute_disparity(decisions, attr)
            if report:
                disparity_reports.append(report)
        
        # Determine overall pass/fail
        severe_disparities = [r for r in disparity_reports if r.disparity_level == DisparityLevel.SEVERE]
        significant_disparities = [r for r in disparity_reports if r.disparity_level == DisparityLevel.SIGNIFICANT]
        
        passed = len(severe_disparities) == 0
        
        # Generate flags
        flags = []
        for report in severe_disparities:
            flags.append(
                f"SEVERE disparity in {report.attribute}: "
                f"{report.lowest_approval_group} approval rate is {report.disparity_ratio:.0%} "
                f"of {report.highest_approval_group}"
            )
        
        warnings = []
        for report in significant_disparities:
            warnings.append(
                f"Significant disparity in {report.attribute}: "
                f"{report.lowest_approval_group} vs {report.highest_approval_group} "
                f"(ratio: {report.disparity_ratio:.0%})"
            )
        
        return AnalysisResult(
            analyzer_name=self.name,
            passed=passed,
            flags=flags,
            warnings=warnings,
            details={
                "total_decisions_analyzed": len(decisions),
                "lookback_days": lookback_days,
                "attributes_checked": attributes_to_check,
                "disparity_reports": [
                    {
                        "attribute": r.attribute,
                        "disparity_level": r.disparity_level.value,
                        "disparity_ratio": r.disparity_ratio,
                        "groups": [
                            {
                                "name": g.group_name,
                                "total": g.total_decisions,
                                "approval_rate": g.approval_rate
                            }
                            for g in r.groups
                        ],
                        "recommendation": r.recommendation
                    }
                    for r in disparity_reports
                ]
            },
            recommendation=self._generate_overall_recommendation(disparity_reports)
        )
    
    async def _get_historical_decisions(
        self,
        decision_type: Optional[str],
        lookback_days: int
    ) -> List[Dict[str, Any]]:
        """Get historical decisions with demographic data."""
        # This would query the decision log / accountability results
        # For now, return placeholder structure
        # In production, this queries the stored AccountabilityResults
        return []
    
    def _analyze_attribute_disparity(
        self,
        decisions: List[Dict[str, Any]],
        attribute: str
    ) -> Optional[DisparityReport]:
        """Analyze disparity for a single attribute."""
        
        # Group decisions by attribute value
        groups: Dict[str, GroupOutcome] = {}
        
        for decision in decisions:
            # Extract attribute value from decision
            attr_value = self._extract_attribute(decision, attribute)
            if not attr_value:
                continue
            
            if attr_value not in groups:
                groups[attr_value] = GroupOutcome(group_name=attr_value)
            
            groups[attr_value].total_decisions += 1
            
            outcome = decision.get("outcome", "").lower()
            if outcome == "approved":
                groups[attr_value].approvals += 1
            elif outcome == "denied":
                groups[attr_value].denials += 1
            else:
                groups[attr_value].needs_review += 1
        
        # Filter groups with sufficient sample size
        valid_groups = [g for g in groups.values() if g.total_decisions >= self.min_group_size]
        
        if len(valid_groups) < 2:
            return None  # Need at least 2 groups to compare
        
        # Find highest and lowest approval rates
        sorted_groups = sorted(valid_groups, key=lambda g: g.approval_rate, reverse=True)
        highest = sorted_groups[0]
        lowest = sorted_groups[-1]
        
        # Calculate disparity ratio
        if highest.approval_rate > 0:
            disparity_ratio = lowest.approval_rate / highest.approval_rate
        else:
            disparity_ratio = 1.0
        
        # Determine disparity level
        if disparity_ratio >= self.minor_threshold:
            level = DisparityLevel.NONE
        elif disparity_ratio >= self.significant_threshold:
            level = DisparityLevel.MINOR
        elif disparity_ratio >= self.severe_threshold:
            level = DisparityLevel.SIGNIFICANT
        else:
            level = DisparityLevel.SEVERE
        
        # Generate recommendation
        if level == DisparityLevel.NONE:
            recommendation = f"No significant disparity detected for {attribute}."
        elif level == DisparityLevel.MINOR:
            recommendation = f"Minor disparity in {attribute}. Monitor for trends."
        elif level == DisparityLevel.SIGNIFICANT:
            recommendation = f"Significant disparity in {attribute}. Review criteria and model behavior."
        else:
            recommendation = f"SEVERE disparity in {attribute}. Immediate review required. Consider pausing automated decisions."
        
        return DisparityReport(
            attribute=attribute,
            groups=list(valid_groups),
            disparity_level=level,
            disparity_ratio=disparity_ratio,
            sample_size_sufficient=True,
            highest_approval_group=highest.group_name,
            lowest_approval_group=lowest.group_name,
            recommendation=recommendation
        )
    
    def _extract_attribute(
        self,
        decision: Dict[str, Any],
        attribute: str
    ) -> Optional[str]:
        """Extract attribute value from decision data."""
        # Look in input_data
        input_data = decision.get("input_data", {})
        
        if attribute == "gender":
            return input_data.get("gender")
        elif attribute == "race_proxy":
            # Inferred from name
            return input_data.get("inferred_race")
        elif attribute == "location":
            loc = input_data.get("location", "")
            # Bucket into regions
            return self._bucket_location(loc)
        elif attribute == "university_tier":
            return input_data.get("university_tier")
        
        return input_data.get(attribute)
    
    def _bucket_location(self, location: str) -> Optional[str]:
        """Bucket location into broad categories."""
        if not location:
            return None
        
        location_lower = location.lower()
        
        # Simple regional bucketing
        northeast = ["new york", "boston", "philadelphia", "dc", "washington"]
        west = ["california", "seattle", "portland", "denver", "san francisco", "la"]
        south = ["texas", "florida", "atlanta", "miami", "austin"]
        midwest = ["chicago", "detroit", "minneapolis", "cleveland"]
        
        for city in northeast:
            if city in location_lower:
                return "Northeast"
        for city in west:
            if city in location_lower:
                return "West"
        for city in south:
            if city in location_lower:
                return "South"
        for city in midwest:
            if city in location_lower:
                return "Midwest"
        
        return "Other"
    
    def _generate_overall_recommendation(
        self,
        reports: List[DisparityReport]
    ) -> str:
        """Generate overall recommendation from all reports."""
        severe = [r for r in reports if r.disparity_level == DisparityLevel.SEVERE]
        significant = [r for r in reports if r.disparity_level == DisparityLevel.SIGNIFICANT]
        
        if severe:
            attrs = ", ".join([r.attribute for r in severe])
            return f"CRITICAL: Severe disparities detected in {attrs}. Immediate review required."
        
        if significant:
            attrs = ", ".join([r.attribute for r in significant])
            return f"WARNING: Significant disparities in {attrs}. Review and monitor."
        
        return "No significant outcome disparities detected. Continue monitoring."
```

---

# PHASE 8: REMAINING OUTPUTS

---

## 8.1 Training Signal Output

**Purpose**: Generate feedback signals that can be used to improve the underlying AI models.

**File**: `backend/outputs/training_signal.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.base import BaseOutput
from core.result import AccountabilityResult, StrategyResult, AnalysisResult


@dataclass
class TrainingExample:
    """A single training example derived from a decision."""
    
    # Input
    input_text: str
    input_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Original output
    original_output: str
    original_decision: str
    original_confidence: float
    
    # Correction (if any)
    was_corrected: bool = False
    corrected_decision: Optional[str] = None
    correction_reason: Optional[str] = None
    
    # Labels for training
    labels: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"bias_present": True, "bias_type": "name", "quality": "poor"}
    
    # Quality indicators
    include_in_training: bool = True
    quality_score: float = 1.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    case_id: str = ""


@dataclass
class TrainingSignal:
    """Complete training signal output."""
    
    # Examples
    positive_examples: List[TrainingExample] = field(default_factory=list)  # Good decisions
    negative_examples: List[TrainingExample] = field(default_factory=list)  # Decisions to avoid
    
    # Aggregate signals
    common_errors: List[str] = field(default_factory=list)
    bias_patterns: List[str] = field(default_factory=list)
    
    # Export format
    format: str = "jsonl"  # jsonl, csv, or custom
    
    # Stats
    total_examples: int = 0
    usable_examples: int = 0


class TrainingSignalOutput(BaseOutput):
    """
    Generates training signals from TrustChain evaluations.
    
    Outputs can be used for:
    - Fine-tuning models
    - RLHF training data
    - Evaluation datasets
    - Error analysis
    
    Usage:
        output = TrainingSignalOutput()
        signal = await output.generate(
            result=accountability_result,
            feedback=human_feedback  # Optional
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("training_signal", config)
        
        self.min_quality_threshold = 0.5
        self.include_corrections_only = config.get("corrections_only", False) if config else False
    
    async def generate(
        self,
        result: AccountabilityResult,
        feedback: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate training signal from evaluation result.
        
        Args:
            result: The TrustChain evaluation result
            feedback: Optional human feedback on this decision
        """
        
        # Extract input/output
        input_data = kwargs.get("input_data", {})
        input_text = self._serialize_input(input_data)
        
        # Determine if this was corrected
        was_corrected = False
        corrected_decision = None
        correction_reason = None
        
        if feedback:
            if hasattr(feedback, 'action') and 'override' in feedback.action.value.lower():
                was_corrected = True
                corrected_decision = feedback.action.value
                correction_reason = getattr(feedback, 'reasoning', '')
        
        # Generate labels from analysis results
        labels = self._extract_labels(result)
        
        # Determine quality score
        quality_score = self._calculate_quality_score(result, feedback)
        
        # Create training example
        example = TrainingExample(
            input_text=input_text,
            input_metadata=input_data,
            original_output=result.primary_reasoning or "",
            original_decision=result.final_decision.value,
            original_confidence=result.overall_confidence,
            was_corrected=was_corrected,
            corrected_decision=corrected_decision,
            correction_reason=correction_reason,
            labels=labels,
            include_in_training=quality_score >= self.min_quality_threshold,
            quality_score=quality_score,
            case_id=result.case_id
        )
        
        # Categorize as positive or negative
        is_positive = not was_corrected and not labels.get("bias_present", False)
        
        # Build output
        signal = TrainingSignal(
            positive_examples=[example] if is_positive else [],
            negative_examples=[example] if not is_positive else [],
            total_examples=1,
            usable_examples=1 if example.include_in_training else 0
        )
        
        return {
            "training_signal": self._serialize_signal(signal),
            "example": {
                "input": example.input_text[:500],
                "output": example.original_output[:500],
                "decision": example.original_decision,
                "was_corrected": example.was_corrected,
                "labels": example.labels,
                "quality_score": example.quality_score,
                "include_in_training": example.include_in_training
            }
        }
    
    def _serialize_input(self, input_data: Dict[str, Any]) -> str:
        """Serialize input data to text for training."""
        parts = []
        for key, value in input_data.items():
            if isinstance(value, str):
                parts.append(f"{key}: {value}")
            elif isinstance(value, list):
                parts.append(f"{key}: {', '.join(str(v) for v in value)}")
        return "\n".join(parts)
    
    def _extract_labels(self, result: AccountabilityResult) -> Dict[str, Any]:
        """Extract training labels from analysis results."""
        labels = {
            "final_decision": result.final_decision.value,
            "confidence": result.overall_confidence,
            "requires_review": result.requires_human_review,
            "bias_present": False,
            "bias_types": [],
            "reasoning_quality": "unknown"
        }
        
        # Check analysis results for bias flags
        for analysis in result.analysis_results:
            if "bias" in analysis.analyzer_name.lower() or "proxy" in analysis.analyzer_name.lower():
                if not analysis.passed:
                    labels["bias_present"] = True
                    labels["bias_types"].extend(analysis.flags)
            
            if "reasoning" in analysis.analyzer_name.lower():
                labels["reasoning_quality"] = analysis.details.get("quality", "unknown")
        
        return labels
    
    def _calculate_quality_score(
        self, 
        result: AccountabilityResult, 
        feedback: Optional[Any]
    ) -> float:
        """Calculate quality score for training example."""
        score = 0.5  # Base score
        
        # Higher confidence = higher quality signal
        score += result.overall_confidence * 0.2
        
        # Human feedback increases quality
        if feedback:
            score += 0.2
        
        # Flagged decisions are valuable for training
        if result.requires_human_review:
            score += 0.1
        
        return min(1.0, score)
    
    def _serialize_signal(self, signal: TrainingSignal) -> Dict[str, Any]:
        """Serialize training signal for export."""
        return {
            "positive_count": len(signal.positive_examples),
            "negative_count": len(signal.negative_examples),
            "total": signal.total_examples,
            "usable": signal.usable_examples,
            "format": signal.format
        }
```

---

## 8.2 Appeal Package Output

**Purpose**: Generate complete documentation for appeals/disputes.

**File**: `backend/outputs/appeal_package.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from core.base import BaseOutput
from core.result import AccountabilityResult


@dataclass
class AppealPackage:
    """Complete appeal documentation package."""
    
    # Header info
    case_id: str
    decision_date: datetime
    decision_type: str
    appellant_name: str
    
    # Decision summary
    original_decision: str
    decision_reasoning: str
    confidence_level: float
    
    # Criteria breakdown
    criteria_met: List[str] = field(default_factory=list)
    criteria_not_met: List[str] = field(default_factory=list)
    criteria_partial: List[str] = field(default_factory=list)
    
    # Evidence considered
    evidence_summary: List[Dict[str, str]] = field(default_factory=list)
    
    # Bias analysis
    bias_checks_performed: List[str] = field(default_factory=list)
    bias_flags: List[str] = field(default_factory=list)
    
    # Appeal information
    appeal_deadline: datetime = field(default_factory=datetime.now)
    appeal_instructions: str = ""
    grounds_for_appeal: List[str] = field(default_factory=list)
    
    # Supporting documents
    audit_trail_hash: str = ""
    
    # Contact
    contact_info: str = ""


class AppealPackageOutput(BaseOutput):
    """
    Generates comprehensive appeal documentation.
    
    Provides everything needed for:
    - Formal appeals
    - Legal discovery
    - FOIA requests
    - Internal reviews
    
    Usage:
        output = AppealPackageOutput()
        package = await output.generate(
            result=accountability_result,
            appellant_info={"name": "Jane Doe"}
        )
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("appeal_package", config)
        
        self.appeal_window_days = config.get("appeal_window_days", 30) if config else 30
        self.organization_name = config.get("organization_name", "Organization") if config else "Organization"
        self.contact_email = config.get("contact_email", "appeals@example.com") if config else "appeals@example.com"
    
    async def generate(
        self,
        result: AccountabilityResult,
        appellant_info: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate appeal package.
        
        Args:
            result: The TrustChain evaluation result
            appellant_info: Information about the person appealing
        """
        
        appellant_name = appellant_info.get("name", "Appellant") if appellant_info else "Appellant"
        
        # Extract criteria breakdown
        criteria_met, criteria_not_met, criteria_partial = self._extract_criteria_breakdown(result)
        
        # Extract evidence summary
        evidence = self._extract_evidence(result)
        
        # Extract bias information
        bias_checks, bias_flags = self._extract_bias_info(result)
        
        # Determine grounds for appeal
        grounds = self._determine_appeal_grounds(result)
        
        # Build package
        package = AppealPackage(
            case_id=result.case_id,
            decision_date=datetime.fromisoformat(result.timestamp) if isinstance(result.timestamp, str) else result.timestamp,
            decision_type=result.decision_type,
            appellant_name=appellant_name,
            original_decision=result.final_decision.value,
            decision_reasoning=result.primary_reasoning or "No reasoning provided",
            confidence_level=result.overall_confidence,
            criteria_met=criteria_met,
            criteria_not_met=criteria_not_met,
            criteria_partial=criteria_partial,
            evidence_summary=evidence,
            bias_checks_performed=bias_checks,
            bias_flags=bias_flags,
            appeal_deadline=datetime.now() + timedelta(days=self.appeal_window_days),
            appeal_instructions=self._generate_appeal_instructions(),
            grounds_for_appeal=grounds,
            audit_trail_hash=result.audit_hash,
            contact_info=f"Submit appeals to: {self.contact_email}"
        )
        
        return {
            "appeal_package": self._format_package(package),
            "pdf_content": self._generate_pdf_content(package),
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "case_id": package.case_id,
                "appeal_deadline": package.appeal_deadline.isoformat()
            }
        }
    
    def _extract_criteria_breakdown(
        self, 
        result: AccountabilityResult
    ) -> tuple:
        """Extract criteria breakdown from result."""
        met = []
        not_met = []
        partial = []
        
        # Look for gap analysis results
        for analysis in result.analysis_results:
            if "gap" in analysis.analyzer_name.lower():
                breakdown = analysis.details.get("criteria_breakdown", [])
                for crit in breakdown:
                    level = crit.get("match_level", "")
                    text = crit.get("criterion", "")
                    
                    if level in ["exceeded", "met"]:
                        met.append(text)
                    elif level == "partial":
                        partial.append(text)
                    elif level in ["missing", "weak"]:
                        not_met.append(text)
        
        return met, not_met, partial
    
    def _extract_evidence(self, result: AccountabilityResult) -> List[Dict[str, str]]:
        """Extract evidence considered."""
        evidence = []
        
        # From strategy results
        for sr in result.strategy_results:
            if hasattr(sr, "evidence"):
                for e in sr.evidence:
                    evidence.append({
                        "source": sr.strategy_name,
                        "evidence": str(e)[:200]
                    })
        
        return evidence[:10]  # Limit to 10 pieces
    
    def _extract_bias_info(self, result: AccountabilityResult) -> tuple:
        """Extract bias analysis information."""
        checks = []
        flags = []
        
        for analysis in result.analysis_results:
            if any(term in analysis.analyzer_name.lower() for term in ["bias", "proxy", "protected", "counterfactual"]):
                checks.append(analysis.analyzer_name)
                flags.extend(analysis.flags)
        
        return checks, flags
    
    def _determine_appeal_grounds(self, result: AccountabilityResult) -> List[str]:
        """Determine valid grounds for appeal."""
        grounds = [
            "New information not available at time of decision",
            "Error in fact (incorrect information was considered)",
            "Procedural error (evaluation process not followed correctly)"
        ]
        
        # Add specific grounds based on result
        if result.requires_human_review:
            grounds.append("Decision was flagged for human review but not adequately reviewed")
        
        for analysis in result.analysis_results:
            if not analysis.passed:
                grounds.append(f"Concerns identified in {analysis.analyzer_name} were not addressed")
        
        return grounds
    
    def _generate_appeal_instructions(self) -> str:
        """Generate appeal instructions."""
        return f"""
APPEAL INSTRUCTIONS

To appeal this decision, please follow these steps:

1. Review this Appeal Package carefully, including all criteria and evidence considered.

2. Prepare your appeal in writing, including:
   - Your case ID (shown above)
   - The specific grounds for your appeal (see "Grounds for Appeal" section)
   - Any new evidence or information you wish to submit
   - A clear statement of why you believe the decision should be reconsidered

3. Submit your appeal by the deadline shown above to:
   {self.contact_email}

4. You will receive confirmation of receipt within 3 business days.

5. Appeals are typically reviewed within 10-15 business days.

6. You will receive a written response with the outcome of your appeal.

Note: Submitting an appeal does not guarantee a change in decision. All appeals
are reviewed based on the merits of the grounds presented and any new evidence.
        """.strip()
    
    def _format_package(self, package: AppealPackage) -> Dict[str, Any]:
        """Format package for JSON output."""
        return {
            "header": {
                "case_id": package.case_id,
                "decision_date": package.decision_date.isoformat(),
                "decision_type": package.decision_type,
                "appellant": package.appellant_name
            },
            "decision": {
                "outcome": package.original_decision,
                "reasoning": package.decision_reasoning,
                "confidence": f"{package.confidence_level:.0%}"
            },
            "criteria_analysis": {
                "met": package.criteria_met,
                "not_met": package.criteria_not_met,
                "partial": package.criteria_partial
            },
            "evidence": package.evidence_summary,
            "bias_analysis": {
                "checks_performed": package.bias_checks_performed,
                "flags": package.bias_flags
            },
            "appeal_info": {
                "deadline": package.appeal_deadline.strftime("%B %d, %Y"),
                "instructions": package.appeal_instructions,
                "valid_grounds": package.grounds_for_appeal,
                "contact": package.contact_info
            },
            "verification": {
                "audit_hash": package.audit_trail_hash
            }
        }
    
    def _generate_pdf_content(self, package: AppealPackage) -> str:
        """Generate content suitable for PDF generation."""
        # This would be used with a PDF library to generate the actual document
        # For now, return structured text
        return f"""
APPEAL PACKAGE
==============

Case ID: {package.case_id}
Decision Date: {package.decision_date.strftime("%B %d, %Y")}
Decision Type: {package.decision_type}
Appellant: {package.appellant_name}

DECISION SUMMARY
----------------
Outcome: {package.original_decision}
Confidence: {package.confidence_level:.0%}

Reasoning:
{package.decision_reasoning}

CRITERIA ANALYSIS
-----------------
Criteria Met:
{chr(10).join('• ' + c for c in package.criteria_met) or 'None'}

Criteria Not Met:
{chr(10).join('• ' + c for c in package.criteria_not_met) or 'None'}

Criteria Partially Met:
{chr(10).join('• ' + c for c in package.criteria_partial) or 'None'}

BIAS ANALYSIS
-------------
Checks Performed: {', '.join(package.bias_checks_performed) or 'Standard checks'}
Flags Raised: {', '.join(package.bias_flags) or 'None'}

APPEAL INFORMATION
------------------
Deadline: {package.appeal_deadline.strftime("%B %d, %Y")}

{package.appeal_instructions}

Valid Grounds for Appeal:
{chr(10).join('• ' + g for g in package.grounds_for_appeal)}

VERIFICATION
------------
Audit Trail Hash: {package.audit_trail_hash}

{package.contact_info}
        """.strip()
```

---

## 8.3 Compliance Report Output

**Purpose**: Generate reports formatted for specific regulatory frameworks (EEOC, ECOA, GDPR).

**File**: `backend/outputs/compliance_report.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from core.base import BaseOutput
from core.result import AccountabilityResult


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""
    EEOC = "eeoc"           # Equal Employment Opportunity Commission
    ECOA = "ecoa"           # Equal Credit Opportunity Act
    FCRA = "fcra"           # Fair Credit Reporting Act
    GDPR = "gdpr"           # General Data Protection Regulation
    CCPA = "ccpa"           # California Consumer Privacy Act
    ADA = "ada"             # Americans with Disabilities Act
    CUSTOM = "custom"


@dataclass
class ComplianceCheckResult:
    """Result of a single compliance check."""
    check_name: str
    requirement: str
    status: str  # "compliant", "non_compliant", "needs_review"
    evidence: str
    recommendation: str = ""


@dataclass
class ComplianceReport:
    """Formal compliance report."""
    
    # Header
    report_id: str
    framework: ComplianceFramework
    generated_at: datetime
    reporting_period: str
    
    # Summary
    overall_status: str  # "compliant", "non_compliant", "partial"
    compliance_score: float  # 0.0 - 1.0
    
    # Checks
    checks: List[ComplianceCheckResult] = field(default_factory=list)
    
    # Statistics
    total_decisions: int = 0
    decisions_with_flags: int = 0
    human_reviews_completed: int = 0
    
    # Findings
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Certification
    preparer: str = ""
    reviewer: str = ""


class ComplianceReportOutput(BaseOutput):
    """
    Generates compliance reports for regulatory frameworks.
    
    Supports:
    - EEOC (employment decisions)
    - ECOA (credit decisions)
    - GDPR (data processing)
    - Custom frameworks
    
    Usage:
        output = ComplianceReportOutput(framework=ComplianceFramework.EEOC)
        report = await output.generate(
            results=list_of_accountability_results,
            period="Q4 2025"
        )
    """
    
    # Compliance requirements by framework
    FRAMEWORK_REQUIREMENTS = {
        ComplianceFramework.EEOC: [
            {
                "check": "disparate_impact",
                "requirement": "No adverse impact on protected groups (80% rule)",
                "analyzer": "outcome_patterns"
            },
            {
                "check": "protected_attribute_consideration",
                "requirement": "No direct consideration of protected attributes",
                "analyzer": "protected_attributes"
            },
            {
                "check": "job_related_criteria",
                "requirement": "Criteria must be job-related and consistent with business necessity",
                "analyzer": "gap_analysis"
            },
            {
                "check": "reasonable_accommodation",
                "requirement": "Process for reasonable accommodation requests",
                "analyzer": "custom"
            }
        ],
        ComplianceFramework.ECOA: [
            {
                "check": "prohibited_factors",
                "requirement": "No use of prohibited factors (race, color, religion, national origin, sex, marital status, age)",
                "analyzer": "protected_attributes"
            },
            {
                "check": "adverse_action_notice",
                "requirement": "Adverse action notices provided with specific reasons",
                "analyzer": "consumer_explanation"
            },
            {
                "check": "statistical_analysis",
                "requirement": "Regular statistical analysis for fair lending",
                "analyzer": "outcome_patterns"
            }
        ],
        ComplianceFramework.GDPR: [
            {
                "check": "automated_decision_disclosure",
                "requirement": "Disclosure of automated decision-making (Article 22)",
                "analyzer": "consumer_explanation"
            },
            {
                "check": "meaningful_information",
                "requirement": "Meaningful information about logic involved",
                "analyzer": "reasoning_quality"
            },
            {
                "check": "human_intervention",
                "requirement": "Right to obtain human intervention",
                "analyzer": "custom"
            },
            {
                "check": "contest_decision",
                "requirement": "Right to contest the decision",
                "analyzer": "appeal_package"
            }
        ]
    }
    
    def __init__(
        self, 
        framework: ComplianceFramework = ComplianceFramework.EEOC,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("compliance_report", config)
        self.framework = framework
    
    async def generate(
        self,
        results: Optional[List[AccountabilityResult]] = None,
        result: Optional[AccountabilityResult] = None,
        period: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate compliance report.
        
        Args:
            results: List of AccountabilityResults for the period
            result: Single result (for single-decision reports)
            period: Reporting period (e.g., "Q4 2025")
        """
        
        # Handle single result
        if result and not results:
            results = [result]
        
        if not results:
            results = []
        
        # Run compliance checks
        checks = await self._run_compliance_checks(results)
        
        # Calculate compliance score
        compliant_checks = sum(1 for c in checks if c.status == "compliant")
        compliance_score = compliant_checks / len(checks) if checks else 1.0
        
        # Determine overall status
        non_compliant = [c for c in checks if c.status == "non_compliant"]
        if non_compliant:
            overall_status = "non_compliant"
        elif any(c.status == "needs_review" for c in checks):
            overall_status = "partial"
        else:
            overall_status = "compliant"
        
        # Generate findings and recommendations
        findings = [c.evidence for c in non_compliant]
        recommendations = [c.recommendation for c in checks if c.recommendation]
        
        # Build report
        report = ComplianceReport(
            report_id=f"CR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            framework=self.framework,
            generated_at=datetime.now(),
            reporting_period=period or f"{datetime.now().strftime('%Y-%m')}",
            overall_status=overall_status,
            compliance_score=compliance_score,
            checks=checks,
            total_decisions=len(results),
            decisions_with_flags=sum(1 for r in results if r.requires_human_review),
            human_reviews_completed=sum(1 for r in results if self._was_reviewed(r)),
            findings=findings,
            recommendations=recommendations
        )
        
        return {
            "report": self._format_report(report),
            "summary": {
                "framework": self.framework.value,
                "status": overall_status,
                "score": f"{compliance_score:.0%}",
                "period": report.reporting_period,
                "total_decisions": report.total_decisions
            },
            "checks": [
                {
                    "check": c.check_name,
                    "status": c.status,
                    "requirement": c.requirement
                }
                for c in checks
            ]
        }
    
    async def _run_compliance_checks(
        self, 
        results: List[AccountabilityResult]
    ) -> List[ComplianceCheckResult]:
        """Run all compliance checks for the framework."""
        
        requirements = self.FRAMEWORK_REQUIREMENTS.get(self.framework, [])
        check_results = []
        
        for req in requirements:
            check_result = await self._run_single_check(req, results)
            check_results.append(check_result)
        
        return check_results
    
    async def _run_single_check(
        self, 
        requirement: Dict[str, str],
        results: List[AccountabilityResult]
    ) -> ComplianceCheckResult:
        """Run a single compliance check."""
        
        check_name = requirement["check"]
        req_text = requirement["requirement"]
        analyzer = requirement["analyzer"]
        
        # Check results for relevant analyzer output
        if analyzer == "custom":
            # Custom checks need manual verification
            return ComplianceCheckResult(
                check_name=check_name,
                requirement=req_text,
                status="needs_review",
                evidence="Manual verification required",
                recommendation="Review process documentation for compliance"
            )
        
        # Look for analyzer results
        relevant_analyses = []
        for result in results:
            for analysis in result.analysis_results:
                if analyzer in analysis.analyzer_name.lower():
                    relevant_analyses.append(analysis)
        
        if not relevant_analyses:
            return ComplianceCheckResult(
                check_name=check_name,
                requirement=req_text,
                status="needs_review",
                evidence=f"No {analyzer} results found",
                recommendation=f"Enable {analyzer} analyzer for compliance monitoring"
            )
        
        # Check for failures
        failures = [a for a in relevant_analyses if not a.passed]
        
        if failures:
            return ComplianceCheckResult(
                check_name=check_name,
                requirement=req_text,
                status="non_compliant",
                evidence=f"{len(failures)} of {len(relevant_analyses)} checks failed. Flags: {failures[0].flags[:2]}",
                recommendation=f"Review and remediate {check_name} failures"
            )
        
        return ComplianceCheckResult(
            check_name=check_name,
            requirement=req_text,
            status="compliant",
            evidence=f"All {len(relevant_analyses)} checks passed"
        )
    
    def _was_reviewed(self, result: AccountabilityResult) -> bool:
        """Check if a result was human-reviewed."""
        # Would check feedback store in production
        return hasattr(result, 'reviewed') and result.reviewed
    
    def _format_report(self, report: ComplianceReport) -> Dict[str, Any]:
        """Format report for output."""
        return {
            "header": {
                "report_id": report.report_id,
                "framework": report.framework.value.upper(),
                "generated": report.generated_at.isoformat(),
                "period": report.reporting_period
            },
            "summary": {
                "overall_status": report.overall_status.upper(),
                "compliance_score": f"{report.compliance_score:.0%}",
                "total_decisions": report.total_decisions,
                "flagged_decisions": report.decisions_with_flags,
                "reviewed_decisions": report.human_reviews_completed
            },
            "compliance_checks": [
                {
                    "check": c.check_name,
                    "requirement": c.requirement,
                    "status": c.status,
                    "evidence": c.evidence,
                    "recommendation": c.recommendation
                }
                for c in report.checks
            ],
            "findings": report.findings,
            "recommendations": report.recommendations,
            "certification": {
                "preparer": report.preparer or "TrustChain Automated Report",
                "reviewer": report.reviewer or "Pending Review",
                "disclaimer": "This report is generated automatically and should be reviewed by compliance personnel."
            }
        }
```

---

# PHASE 9: REMAINING STRATEGIES

---

## 9.1 Constitutional Principles Check Strategy

**Purpose**: Verify AI reasoning against predefined rules/principles.

**File**: `backend/strategies/constitutional_check.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

from core.base import BaseStrategy
from core.result import StrategyResult, DecisionOutcome


class ViolationSeverity(str, Enum):
    """Severity of principle violation."""
    CRITICAL = "critical"    # Must reject
    HIGH = "high"            # Strongly consider rejection
    MEDIUM = "medium"        # Flag for review
    LOW = "low"              # Warning only


@dataclass
class Principle:
    """A constitutional principle to check."""
    id: str
    name: str
    description: str
    check_prompt: str  # Prompt to evaluate against this principle
    violation_severity: ViolationSeverity = ViolationSeverity.MEDIUM
    category: str = "general"


@dataclass
class PrincipleViolation:
    """A detected principle violation."""
    principle: Principle
    violated: bool
    confidence: float
    explanation: str
    evidence: str = ""


# Default principles for common use cases
DEFAULT_HIRING_PRINCIPLES = [
    Principle(
        id="no_protected_class",
        name="Protected Class Exclusion",
        description="Decision must not be based on protected class membership",
        check_prompt="Does this reasoning reference or consider race, gender, age, religion, national origin, disability, or genetic information as a factor in the decision?",
        violation_severity=ViolationSeverity.CRITICAL,
        category="discrimination"
    ),
    Principle(
        id="job_related",
        name="Job-Related Criteria",
        description="All criteria must be job-related and necessary",
        check_prompt="Are all the criteria used in this decision directly related to job performance and business necessity?",
        violation_severity=ViolationSeverity.HIGH,
        category="relevance"
    ),
    Principle(
        id="consistent_application",
        name="Consistent Application",
        description="Criteria must be applied consistently across candidates",
        check_prompt="Is this decision applying the same standards that would be applied to any other candidate?",
        violation_severity=ViolationSeverity.HIGH,
        category="fairness"
    ),
    Principle(
        id="no_stereotyping",
        name="No Stereotyping",
        description="Decision must not rely on stereotypes or generalizations",
        check_prompt="Does this reasoning rely on stereotypes, generalizations, or assumptions about groups rather than individual qualifications?",
        violation_severity=ViolationSeverity.CRITICAL,
        category="discrimination"
    ),
    Principle(
        id="explainable",
        name="Explainability",
        description="Decision reasoning must be explainable and specific",
        check_prompt="Is the reasoning specific, clear, and explainable, or is it vague and unclear?",
        violation_severity=ViolationSeverity.MEDIUM,
        category="transparency"
    )
]

DEFAULT_LENDING_PRINCIPLES = [
    Principle(
        id="ecoa_compliance",
        name="ECOA Compliance",
        description="No consideration of prohibited factors under ECOA",
        check_prompt="Does this decision consider race, color, religion, national origin, sex, marital status, age (if applicant can legally contract), or public assistance status?",
        violation_severity=ViolationSeverity.CRITICAL,
        category="regulatory"
    ),
    Principle(
        id="ability_to_repay",
        name="Ability to Repay",
        description="Decision must be based on ability to repay",
        check_prompt="Is this decision based on the applicant's demonstrated ability to repay the obligation?",
        violation_severity=ViolationSeverity.HIGH,
        category="underwriting"
    ),
    Principle(
        id="adverse_action_reasons",
        name="Specific Adverse Action Reasons",
        description="Denials must have specific, articulable reasons",
        check_prompt="If denying, are there specific, articulable reasons based on creditworthiness factors?",
        violation_severity=ViolationSeverity.HIGH,
        category="regulatory"
    )
]


class ConstitutionalCheckStrategy(BaseStrategy):
    """
    Strategy that checks AI decisions against constitutional principles.
    
    Inspired by Constitutional AI, this strategy verifies that reasoning
    and decisions comply with predefined rules and principles.
    
    Usage:
        strategy = ConstitutionalCheckStrategy(
            principles=DEFAULT_HIRING_PRINCIPLES
        )
        result = await strategy.evaluate(
            input_data=application,
            existing_decision=preliminary_decision,
            existing_reasoning=preliminary_reasoning
        )
    """
    
    def __init__(
        self, 
        principles: Optional[List[Principle]] = None,
        llm_provider: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("constitutional_check", config)
        self.principles = principles or DEFAULT_HIRING_PRINCIPLES
        self.llm = llm_provider
    
    async def evaluate(
        self,
        input_data: Dict[str, Any],
        existing_decision: Optional[str] = None,
        existing_reasoning: Optional[str] = None,
        **kwargs
    ) -> StrategyResult:
        """
        Check decision against constitutional principles.
        
        Args:
            input_data: The original input being evaluated
            existing_decision: A preliminary decision to check
            existing_reasoning: The reasoning to evaluate
        """
        
        if not existing_reasoning:
            return StrategyResult(
                strategy_name=self.name,
                decision=DecisionOutcome.NEEDS_REVIEW,
                confidence=0.0,
                reasoning="No reasoning provided to evaluate against principles"
            )
        
        # Check each principle
        violations = []
        for principle in self.principles:
            violation = await self._check_principle(
                principle, 
                existing_reasoning, 
                input_data
            )
            if violation.violated:
                violations.append(violation)
        
        # Determine outcome
        critical_violations = [v for v in violations if v.principle.violation_severity == ViolationSeverity.CRITICAL]
        high_violations = [v for v in violations if v.principle.violation_severity == ViolationSeverity.HIGH]
        
        if critical_violations:
            decision = DecisionOutcome.DENIED
            confidence = 0.95
        elif high_violations:
            decision = DecisionOutcome.NEEDS_REVIEW
            confidence = 0.7
        elif violations:
            decision = DecisionOutcome.APPROVED  # Pass through with warnings
            confidence = 0.8
        else:
            decision = DecisionOutcome.APPROVED
            confidence = 0.9
        
        # Generate reasoning
        if violations:
            reasoning = f"Constitutional check found {len(violations)} violation(s): "
            reasoning += "; ".join([f"{v.principle.name}: {v.explanation}" for v in violations[:3]])
        else:
            reasoning = f"Decision passes all {len(self.principles)} constitutional principles"
        
        return StrategyResult(
            strategy_name=self.name,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "principles_checked": len(self.principles),
                "violations_found": len(violations),
                "critical_violations": len(critical_violations),
                "high_violations": len(high_violations),
                "violations": [
                    {
                        "principle": v.principle.name,
                        "severity": v.principle.violation_severity.value,
                        "explanation": v.explanation
                    }
                    for v in violations
                ]
            }
        )
    
    async def _check_principle(
        self,
        principle: Principle,
        reasoning: str,
        input_data: Dict[str, Any]
    ) -> PrincipleViolation:
        """Check reasoning against a single principle."""
        
        # If we have an LLM, use it for sophisticated checking
        if self.llm:
            return await self._llm_check_principle(principle, reasoning, input_data)
        
        # Otherwise, use keyword-based heuristics
        return self._heuristic_check_principle(principle, reasoning)
    
    async def _llm_check_principle(
        self,
        principle: Principle,
        reasoning: str,
        input_data: Dict[str, Any]
    ) -> PrincipleViolation:
        """Use LLM to check principle."""
        
        prompt = f"""
You are evaluating whether a decision's reasoning violates a constitutional principle.

PRINCIPLE: {principle.name}
DESCRIPTION: {principle.description}
CHECK: {principle.check_prompt}

REASONING TO EVALUATE:
{reasoning}

Does this reasoning violate the principle? Respond with:
- VIOLATED: Yes or No
- CONFIDENCE: 0.0 to 1.0
- EXPLANATION: Brief explanation

Format your response exactly as:
VIOLATED: [Yes/No]
CONFIDENCE: [0.0-1.0]
EXPLANATION: [Your explanation]
        """
        
        # Would call LLM here
        # response = await self.llm.complete(prompt)
        
        # Parse response and return PrincipleViolation
        # For now, return not violated
        return PrincipleViolation(
            principle=principle,
            violated=False,
            confidence=0.8,
            explanation="LLM check not implemented"
        )
    
    def _heuristic_check_principle(
        self,
        principle: Principle,
        reasoning: str
    ) -> PrincipleViolation:
        """Use heuristics to check principle."""
        
        reasoning_lower = reasoning.lower()
        
        # Define keywords for each principle category
        violation_keywords = {
            "no_protected_class": [
                "race", "gender", "sex", "age", "religion", "disability",
                "national origin", "genetic", "pregnancy", "veteran"
            ],
            "no_stereotyping": [
                "typically", "usually", "tend to", "people like",
                "that type", "those people", "stereotype"
            ],
            "job_related": [],  # Hard to detect with keywords
            "consistent_application": [],
            "explainable": ["unclear", "vague", "uncertain", "maybe"]
        }
        
        keywords = violation_keywords.get(principle.id, [])
        found_keywords = [kw for kw in keywords if kw in reasoning_lower]
        
        if found_keywords:
            return PrincipleViolation(
                principle=principle,
                violated=True,
                confidence=0.7,
                explanation=f"Found concerning keywords: {', '.join(found_keywords)}",
                evidence=", ".join(found_keywords)
            )
        
        return PrincipleViolation(
            principle=principle,
            violated=False,
            confidence=0.6,
            explanation="No obvious violations detected (heuristic check)"
        )
```

---

## 9.2 Historical Consistency Strategy

**Purpose**: Compare decision to similar past cases for consistency.

**File**: `backend/strategies/historical_consistency.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from core.base import BaseStrategy
from core.result import StrategyResult, DecisionOutcome


@dataclass
class SimilarCase:
    """A similar historical case."""
    case_id: str
    similarity_score: float
    decision: str
    timestamp: datetime
    key_factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsistencyAnalysis:
    """Analysis of consistency with historical cases."""
    similar_cases: List[SimilarCase]
    consistency_score: float  # 0.0 = inconsistent, 1.0 = perfectly consistent
    majority_decision: str
    is_outlier: bool


class HistoricalConsistencyStrategy(BaseStrategy):
    """
    Strategy that compares decisions to similar historical cases.
    
    Flags potential inconsistencies where similar cases got different outcomes.
    
    Usage:
        strategy = HistoricalConsistencyStrategy(case_store)
        result = await strategy.evaluate(
            input_data=application,
            proposed_decision="approved"
        )
    """
    
    def __init__(
        self,
        case_store: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__("historical_consistency", config)
        self.case_store = case_store
        
        self.similarity_threshold = 0.7
        self.min_similar_cases = 3
        self.consistency_threshold = 0.6  # Below this = inconsistent
    
    async def evaluate(
        self,
        input_data: Dict[str, Any],
        proposed_decision: Optional[str] = None,
        **kwargs
    ) -> StrategyResult:
        """
        Evaluate consistency with historical cases.
        
        Args:
            input_data: Current case data
            proposed_decision: The proposed decision to check
        """
        
        if not self.case_store:
            return StrategyResult(
                strategy_name=self.name,
                decision=DecisionOutcome.APPROVED,  # Pass through
                confidence=0.5,
                reasoning="No case store configured for historical comparison"
            )
        
        # Find similar cases
        similar_cases = await self._find_similar_cases(input_data)
        
        if len(similar_cases) < self.min_similar_cases:
            return StrategyResult(
                strategy_name=self.name,
                decision=DecisionOutcome.APPROVED,
                confidence=0.6,
                reasoning=f"Insufficient historical data ({len(similar_cases)} similar cases found, need {self.min_similar_cases})",
                metadata={"similar_cases_found": len(similar_cases)}
            )
        
        # Analyze consistency
        analysis = self._analyze_consistency(similar_cases, proposed_decision)
        
        # Determine outcome
        if analysis.is_outlier and analysis.consistency_score < self.consistency_threshold:
            decision = DecisionOutcome.NEEDS_REVIEW
            confidence = 0.8
            reasoning = (
                f"Proposed decision '{proposed_decision}' is inconsistent with "
                f"{len(similar_cases)} similar cases. Majority decision was "
                f"'{analysis.majority_decision}' (consistency: {analysis.consistency_score:.0%})"
            )
        else:
            decision = DecisionOutcome.APPROVED
            confidence = analysis.consistency_score
            reasoning = (
                f"Decision is consistent with {len(similar_cases)} similar cases "
                f"(consistency score: {analysis.consistency_score:.0%})"
            )
        
        return StrategyResult(
            strategy_name=self.name,
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "similar_cases": len(similar_cases),
                "consistency_score": analysis.consistency_score,
                "majority_decision": analysis.majority_decision,
                "is_outlier": analysis.is_outlier,
                "case_summaries": [
                    {
                        "case_id": c.case_id,
                        "similarity": c.similarity_score,
                        "decision": c.decision
                    }
                    for c in similar_cases[:5]
                ]
            }
        )
    
    async def _find_similar_cases(
        self,
        input_data: Dict[str, Any]
    ) -> List[SimilarCase]:
        """Find similar historical cases."""
        
        # Would query case store with similarity search
        # For now, return empty list
        # In production, this could use:
        # - Vector similarity search
        # - Feature-based matching
        # - ML-based similarity models
        
        return []
    
    def _analyze_consistency(
        self,
        similar_cases: List[SimilarCase],
        proposed_decision: Optional[str]
    ) -> ConsistencyAnalysis:
        """Analyze consistency with similar cases."""
        
        if not similar_cases:
            return ConsistencyAnalysis(
                similar_cases=[],
                consistency_score=1.0,
                majority_decision="",
                is_outlier=False
            )
        
        # Count decisions
        decision_counts: Dict[str, int] = {}
        for case in similar_cases:
            decision_counts[case.decision] = decision_counts.get(case.decision, 0) + 1
        
        # Find majority
        majority_decision = max(decision_counts, key=decision_counts.get)
        majority_count = decision_counts[majority_decision]
        
        # Calculate consistency score
        consistency_score = majority_count / len(similar_cases)
        
        # Check if proposed decision is an outlier
        is_outlier = False
        if proposed_decision:
            proposed_count = decision_counts.get(proposed_decision, 0)
            is_outlier = proposed_count < majority_count * 0.5
        
        return ConsistencyAnalysis(
            similar_cases=similar_cases,
            consistency_score=consistency_score,
            majority_decision=majority_decision,
            is_outlier=is_outlier
        )
```

---

# PHASE 10: TESTBED MODE

---

## 10.1 Testbed Mode

**Purpose**: Allow companies to validate TrustChain on historical data before deploying.

**File**: `backend/services/testbed.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from services.trustchain import TrustChain
from core.config import TrustChainConfig
from core.result import AccountabilityResult, DecisionOutcome


@dataclass
class TestCase:
    """A single test case for validation."""
    case_id: str
    input_data: Dict[str, Any]
    expected_decision: Optional[str] = None  # For labeled data
    actual_historical_decision: Optional[str] = None  # What actually happened
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of running a test case."""
    test_case: TestCase
    trustchain_result: AccountabilityResult
    
    # Comparison with expected/historical
    matches_expected: Optional[bool] = None
    matches_historical: Optional[bool] = None
    
    # Would TrustChain have flagged this?
    would_have_flagged: bool = False
    flags_raised: List[str] = field(default_factory=list)


@dataclass
class TestbedReport:
    """Complete testbed validation report."""
    
    # Summary
    total_cases: int = 0
    cases_processed: int = 0
    cases_failed: int = 0
    
    # Agreement metrics
    agreement_with_historical: float = 0.0
    agreement_with_expected: float = 0.0
    
    # Flag metrics
    cases_flagged: int = 0
    flag_rate: float = 0.0
    
    # False positive/negative estimates
    estimated_false_positives: int = 0  # Flagged but historical was fine
    estimated_false_negatives: int = 0  # Didn't flag but should have
    
    # Bias detection
    bias_flags_raised: int = 0
    bias_types_detected: List[str] = field(default_factory=list)
    
    # Performance
    avg_processing_time_ms: float = 0.0
    
    # Individual results
    results: List[TestResult] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)


class TrustChainTestbed:
    """
    Testbed for validating TrustChain on historical data.
    
    Allows companies to:
    - Test TrustChain config on past decisions
    - See what would have been flagged
    - Tune sensitivity before deployment
    - Build confidence in the system
    
    Usage:
        testbed = TrustChainTestbed(config="configs/hiring.yaml")
        
        # Load historical cases
        testbed.load_cases(historical_decisions)
        
        # Run validation
        report = await testbed.run()
        
        # Review results
        print(report.recommendations)
    """
    
    def __init__(
        self,
        config: Optional[str] = None,
        trustchain_config: Optional[TrustChainConfig] = None
    ):
        if config:
            self.tc_config = TrustChainConfig.from_yaml(config)
        else:
            self.tc_config = trustchain_config or TrustChainConfig()
        
        self.test_cases: List[TestCase] = []
        self.results: List[TestResult] = []
    
    def load_cases(self, cases: List[Dict[str, Any]]):
        """
        Load test cases from historical data.
        
        Args:
            cases: List of dicts with:
                - case_id: Unique identifier
                - input_data: The original input
                - actual_decision: What decision was actually made
                - expected_decision: (Optional) What decision should have been made
        """
        for case_data in cases:
            case = TestCase(
                case_id=case_data.get("case_id", f"case_{len(self.test_cases)}"),
                input_data=case_data.get("input_data", {}),
                expected_decision=case_data.get("expected_decision"),
                actual_historical_decision=case_data.get("actual_decision"),
                metadata=case_data.get("metadata", {})
            )
            self.test_cases.append(case)
    
    def load_cases_from_csv(self, csv_path: str):
        """Load test cases from CSV file."""
        import csv
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            cases = list(reader)
        
        self.load_cases(cases)
    
    async def run(
        self,
        parallel: bool = True,
        max_concurrent: int = 10,
        progress_callback: Optional[callable] = None
    ) -> TestbedReport:
        """
        Run testbed validation.
        
        Args:
            parallel: Run cases in parallel
            max_concurrent: Max concurrent evaluations
            progress_callback: Called with (completed, total) for progress updates
        """
        
        # Initialize TrustChain
        tc = TrustChain(config=self.tc_config, dry_run=True)
        
        self.results = []
        start_time = datetime.now()
        
        if parallel:
            # Run in parallel with semaphore
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_case(case: TestCase) -> TestResult:
                async with semaphore:
                    return await self._run_single_case(tc, case)
            
            tasks = [process_case(case) for case in self.test_cases]
            
            for i, coro in enumerate(asyncio.as_completed(tasks)):
                result = await coro
                self.results.append(result)
                if progress_callback:
                    progress_callback(i + 1, len(self.test_cases))
        else:
            # Run sequentially
            for i, case in enumerate(self.test_cases):
                result = await self._run_single_case(tc, case)
                self.results.append(result)
                if progress_callback:
                    progress_callback(i + 1, len(self.test_cases))
        
        end_time = datetime.now()
        
        # Generate report
        report = self._generate_report(start_time, end_time)
        
        return report
    
    async def _run_single_case(
        self, 
        tc: TrustChain, 
        case: TestCase
    ) -> TestResult:
        """Run TrustChain on a single test case."""
        
        try:
            result = await tc.evaluate(
                case_id=case.case_id,
                input_data=case.input_data
            )
            
            # Compare with expected/historical
            matches_expected = None
            matches_historical = None
            
            if case.expected_decision:
                matches_expected = result.final_decision.value.lower() == case.expected_decision.lower()
            
            if case.actual_historical_decision:
                matches_historical = result.final_decision.value.lower() == case.actual_historical_decision.lower()
            
            # Collect flags
            flags = []
            for analysis in result.analysis_results:
                flags.extend(analysis.flags)
            
            return TestResult(
                test_case=case,
                trustchain_result=result,
                matches_expected=matches_expected,
                matches_historical=matches_historical,
                would_have_flagged=result.requires_human_review,
                flags_raised=flags
            )
        
        except Exception as e:
            # Create failed result
            return TestResult(
                test_case=case,
                trustchain_result=None,
                matches_expected=None,
                matches_historical=None,
                would_have_flagged=False,
                flags_raised=[f"ERROR: {str(e)}"]
            )
    
    def _generate_report(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> TestbedReport:
        """Generate testbed report from results."""
        
        total = len(self.test_cases)
        processed = len([r for r in self.results if r.trustchain_result is not None])
        failed = total - processed
        
        # Agreement metrics
        historical_matches = [r for r in self.results if r.matches_historical is True]
        expected_matches = [r for r in self.results if r.matches_expected is True]
        
        agreement_historical = len(historical_matches) / processed if processed > 0 else 0
        agreement_expected = len(expected_matches) / processed if processed > 0 else 0
        
        # Flag metrics
        flagged = [r for r in self.results if r.would_have_flagged]
        flag_rate = len(flagged) / processed if processed > 0 else 0
        
        # Bias detection
        bias_flags = []
        for r in self.results:
            for flag in r.flags_raised:
                if any(term in flag.lower() for term in ["bias", "proxy", "protected", "discrimination"]):
                    bias_flags.append(flag)
        
        bias_types = list(set(bias_flags))
        
        # Processing time
        duration_ms = (end_time - start_time).total_seconds() * 1000
        avg_time = duration_ms / processed if processed > 0 else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            agreement_historical,
            flag_rate,
            len(bias_flags),
            processed
        )
        
        return TestbedReport(
            total_cases=total,
            cases_processed=processed,
            cases_failed=failed,
            agreement_with_historical=agreement_historical,
            agreement_with_expected=agreement_expected,
            cases_flagged=len(flagged),
            flag_rate=flag_rate,
            bias_flags_raised=len(bias_flags),
            bias_types_detected=bias_types[:10],
            avg_processing_time_ms=avg_time,
            results=self.results,
            recommendations=recommendations
        )
    
    def _generate_recommendations(
        self,
        agreement: float,
        flag_rate: float,
        bias_flags: int,
        total: int
    ) -> List[str]:
        """Generate recommendations based on testbed results."""
        recommendations = []
        
        if agreement < 0.7:
            recommendations.append(
                f"Low agreement with historical decisions ({agreement:.0%}). "
                f"Review TrustChain configuration or historical decision quality."
            )
        
        if flag_rate > 0.3:
            recommendations.append(
                f"High flag rate ({flag_rate:.0%}). "
                f"Consider adjusting sensitivity to reduce review burden."
            )
        elif flag_rate < 0.05:
            recommendations.append(
                f"Very low flag rate ({flag_rate:.0%}). "
                f"Consider increasing sensitivity to catch more potential issues."
            )
        
        if bias_flags > 0:
            recommendations.append(
                f"Detected {bias_flags} potential bias issues in historical decisions. "
                f"Review these cases and consider remediation."
            )
        
        if not recommendations:
            recommendations.append(
                "Testbed results look healthy. Consider proceeding to production deployment."
            )
        
        return recommendations
    
    def export_results(self, output_path: str, format: str = "json"):
        """Export testbed results to file."""
        import json
        
        if format == "json":
            with open(output_path, 'w') as f:
                json.dump({
                    "results": [
                        {
                            "case_id": r.test_case.case_id,
                            "decision": r.trustchain_result.final_decision.value if r.trustchain_result else "ERROR",
                            "confidence": r.trustchain_result.overall_confidence if r.trustchain_result else 0,
                            "flagged": r.would_have_flagged,
                            "flags": r.flags_raised,
                            "matches_historical": r.matches_historical
                        }
                        for r in self.results
                    ]
                }, f, indent=2)
```

---

## API Endpoints for Testbed

**Update**: `backend/app.py`

```python
from services.testbed import TrustChainTestbed

testbed_router = APIRouter(prefix="/api/v2/testbed", tags=["testbed"])


@testbed_router.post("/run")
async def run_testbed(
    config_path: str = "configs/hiring.yaml",
    cases: List[Dict[str, Any]] = []
):
    """
    Run testbed validation on provided cases.
    
    Args:
        config_path: Path to TrustChain config
        cases: List of test cases with input_data and actual_decision
    """
    testbed = TrustChainTestbed(config=config_path)
    testbed.load_cases(cases)
    
    report = await testbed.run()
    
    return {
        "summary": {
            "total_cases": report.total_cases,
            "processed": report.cases_processed,
            "agreement_rate": f"{report.agreement_with_historical:.0%}",
            "flag_rate": f"{report.flag_rate:.0%}",
            "bias_issues_found": report.bias_flags_raised
        },
        "recommendations": report.recommendations
    }


@testbed_router.post("/upload-csv")
async def upload_testbed_csv(file: UploadFile):
    """Upload CSV of test cases."""
    # Save file, create testbed, return preview
    pass


@testbed_router.get("/report/{testbed_id}")
async def get_testbed_report(testbed_id: str):
    """Get full report for a completed testbed run."""
    pass
```

---

## Phase 7-10 TODO Checklist

```
PHASE 7: REMAINING ANALYZERS
[ ] Create backend/analyzers/gap_analysis.py
[ ] Implement GapAnalysisAnalyzer
[ ] Tests for gap analysis
[ ] Create backend/analyzers/reasoning_quality.py
[ ] Implement ReasoningQualityAnalyzer
[ ] Tests for reasoning quality
[ ] Create backend/analyzers/confidence_calibration.py
[ ] Implement ConfidenceCalibrationAnalyzer
[ ] Tests for confidence calibration
[ ] Create backend/analyzers/outcome_patterns.py
[ ] Implement OutcomePatternAnalyzer
[ ] Tests for outcome patterns

PHASE 8: REMAINING OUTPUTS
[ ] Create backend/outputs/training_signal.py
[ ] Implement TrainingSignalOutput
[ ] Tests for training signal
[ ] Create backend/outputs/appeal_package.py
[ ] Implement AppealPackageOutput
[ ] Tests for appeal package
[ ] Create backend/outputs/compliance_report.py
[ ] Implement ComplianceReportOutput with EEOC/ECOA/GDPR
[ ] Tests for compliance reports

PHASE 9: REMAINING STRATEGIES
[ ] Create backend/strategies/constitutional_check.py
[ ] Implement ConstitutionalCheckStrategy
[ ] Define DEFAULT_HIRING_PRINCIPLES
[ ] Define DEFAULT_LENDING_PRINCIPLES
[ ] Tests for constitutional check
[ ] Create backend/strategies/historical_consistency.py
[ ] Implement HistoricalConsistencyStrategy
[ ] Tests for historical consistency

PHASE 10: TESTBED MODE
[ ] Create backend/services/testbed.py
[ ] Implement TrustChainTestbed
[ ] Implement TestbedReport generation
[ ] Add testbed API endpoints
[ ] Tests for testbed mode
[ ] Add CSV import for test cases
[ ] Add result export functionality
```

---

## File Structure After Completion

```
backend/
├── analyzers/
│   ├── __init__.py
│   ├── protected_attributes.py     # Phase 2
│   ├── proxy_variables.py          # Phase 2
│   ├── counterfactual_generator.py # Phase 5
│   ├── counterfactual_fairness.py  # Phase 5
│   ├── gap_analysis.py             # Phase 7 NEW
│   ├── reasoning_quality.py        # Phase 7 NEW
│   ├── confidence_calibration.py   # Phase 7 NEW
│   └── outcome_patterns.py         # Phase 7 NEW
│
├── outputs/
│   ├── __init__.py
│   ├── internal_audit.py           # Phase 2
│   ├── consumer_explanation.py     # Phase 2
│   ├── training_signal.py          # Phase 8 NEW
│   ├── appeal_package.py           # Phase 8 NEW
│   └── compliance_report.py        # Phase 8 NEW
│
├── strategies/
│   ├── __init__.py
│   ├── multi_model_consensus.py    # Phase 2
│   ├── criteria_decomposition.py   # Phase 2
│   ├── adversarial_review.py       # Phase 2
│   ├── constitutional_check.py     # Phase 9 NEW
│   └── historical_consistency.py   # Phase 9 NEW
│
├── services/
│   ├── trustchain.py               # Core service
│   └── testbed.py                  # Phase 10 NEW
│
└── tests/
    ├── test_gap_analysis.py        # Phase 7
    ├── test_reasoning_quality.py   # Phase 7
    ├── test_compliance.py          # Phase 8
    ├── test_constitutional.py      # Phase 9
    └── test_testbed.py             # Phase 10
```

---

*Document generated November 2025. Ship it.*

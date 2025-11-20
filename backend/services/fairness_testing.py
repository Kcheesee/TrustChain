"""
Fairness Testing for TrustChain.

Implements counterfactual fairness testing and demographic parity analysis
to ensure AI decisions are not discriminatory.

Key Concepts:
- Counterfactual Fairness: Decision shouldn't change if protected attributes change
- Demographic Parity: Similar approval rates across demographic groups
- Individual Fairness: Similar individuals should get similar decisions

Built with 🤝 by Kareem & Claude (January 2025)
"Making AI accountable, one decision at a time"
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from copy import deepcopy

logger = logging.getLogger(__name__)


class ProtectedAttribute(str, Enum):
    """Protected attributes under civil rights law."""
    RACE = "race"
    ETHNICITY = "ethnicity"
    AGE = "age"
    GENDER = "gender"
    RELIGION = "religion"
    DISABILITY = "disability"
    SEXUAL_ORIENTATION = "sexual_orientation"
    NATIONAL_ORIGIN = "national_origin"
    PREGNANCY = "pregnancy"
    VETERAN_STATUS = "veteran_status"


@dataclass
class FairnessTestResult:
    """Result of a fairness test."""
    test_name: str
    passed: bool
    fairness_score: float  # 0-1, higher is more fair
    details: Dict[str, Any]
    recommendation: str
    severity: str  # "low", "medium", "high", "critical"


class CounterfactualFairnessTester:
    """
    Test counterfactual fairness of decisions.
    
    Principle: If we change only protected attributes (e.g., age, race),
    the decision should remain the same.
    
    Example:
        tester = CounterfactualFairnessTester()
        result = tester.test_decision(
            decision_func=make_decision,
            input_data={"age": 25, "income": 50000},
            protected_attrs=["age"]
        )
    """
    
    def __init__(self, tolerance: float = 0.0):
        """
        Initialize fairness tester.
        
        Args:
            tolerance: Acceptable difference in outcomes (0.0 = strict)
        """
        self.tolerance = tolerance
        self.attribute_variations = {
            ProtectedAttribute.AGE: [25, 35, 45, 55, 65],
            ProtectedAttribute.GENDER: ["male", "female", "non-binary"],
            ProtectedAttribute.RACE: ["white", "black", "asian", "hispanic", "other"],
            ProtectedAttribute.ETHNICITY: ["hispanic", "non-hispanic"],
        }
    
    async def test_decision(
        self,
        decision_func: Callable,
        input_data: Dict[str, Any],
        protected_attrs: List[str],
        **kwargs
    ) -> FairnessTestResult:
        """
        Test if decision is fair across protected attribute variations.
        
        Args:
            decision_func: Async function that makes decisions
            input_data: Original input data
            protected_attrs: List of protected attributes to test
            **kwargs: Additional args for decision_func
            
        Returns:
            FairnessTestResult with test outcomes
        """
        logger.info(f"Testing counterfactual fairness for: {protected_attrs}")
        
        # Get baseline decision
        baseline_decision = await decision_func(input_data, **kwargs)
        baseline_outcome = baseline_decision.final_decision
        
        # Test variations
        outcomes_by_variation = {}
        total_tests = 0
        fair_tests = 0
        
        for attr in protected_attrs:
            if attr not in self.attribute_variations:
                logger.warning(f"No variations defined for {attr}, skipping")
                continue
            
            for variation in self.attribute_variations[attr]:
                # Create modified input
                modified_data = deepcopy(input_data)
                modified_data[attr] = variation
                
                # Get decision with modified data
                modified_decision = await decision_func(modified_data, **kwargs)
                modified_outcome = modified_decision.final_decision
                
                # Compare outcomes
                total_tests += 1
                if modified_outcome == baseline_outcome:
                    fair_tests += 1
                else:
                    outcomes_by_variation[f"{attr}={variation}"] = modified_outcome
                    logger.warning(
                        f"Fairness violation: {attr}={variation} "
                        f"changed decision from {baseline_outcome} to {modified_outcome}"
                    )
        
        # Calculate fairness score
        fairness_score = fair_tests / total_tests if total_tests > 0 else 1.0
        passed = fairness_score >= (1.0 - self.tolerance)
        
        # Determine severity
        if fairness_score < 0.5:
            severity = "critical"
        elif fairness_score < 0.7:
            severity = "high"
        elif fairness_score < 0.9:
            severity = "medium"
        else:
            severity = "low"
        
        # Generate recommendation
        if passed:
            recommendation = "Decision passes counterfactual fairness test"
        else:
            recommendation = (
                f"FAIRNESS VIOLATION: Decision changes based on protected attributes. "
                f"Only {fair_tests}/{total_tests} variations maintained same outcome. "
                f"Review decision logic for potential discrimination."
            )
        
        return FairnessTestResult(
            test_name="Counterfactual Fairness",
            passed=passed,
            fairness_score=fairness_score,
            details={
                "baseline_outcome": baseline_outcome.value if baseline_outcome else None,
                "total_variations_tested": total_tests,
                "fair_variations": fair_tests,
                "violations": outcomes_by_variation,
                "tested_attributes": protected_attrs
            },
            recommendation=recommendation,
            severity=severity
        )


class DemographicParityAnalyzer:
    """
    Analyze demographic parity across groups.
    
    Principle: Approval rates should be similar across demographic groups.
    
    Example:
        analyzer = DemographicParityAnalyzer()
        result = analyzer.analyze(
            decisions_by_group={
                "age_25-35": [approved, approved, denied],
                "age_55-65": [denied, denied, approved]
            }
        )
    """
    
    def __init__(self, max_disparity: float = 0.2):
        """
        Initialize demographic parity analyzer.
        
        Args:
            max_disparity: Maximum acceptable disparity (default 20%)
        """
        self.max_disparity = max_disparity
    
    def analyze(
        self,
        decisions_by_group: Dict[str, List[str]]
    ) -> FairnessTestResult:
        """
        Analyze demographic parity across groups.
        
        Args:
            decisions_by_group: Dict mapping group names to list of decisions
            
        Returns:
            FairnessTestResult with parity analysis
        """
        logger.info(f"Analyzing demographic parity for {len(decisions_by_group)} groups")
        
        # Calculate approval rates per group
        approval_rates = {}
        for group, decisions in decisions_by_group.items():
            if not decisions:
                continue
            
            approved = sum(1 for d in decisions if d in ["approved", "APPROVED"])
            approval_rates[group] = approved / len(decisions)
        
        if not approval_rates:
            return FairnessTestResult(
                test_name="Demographic Parity",
                passed=True,
                fairness_score=1.0,
                details={"error": "No data to analyze"},
                recommendation="Insufficient data for demographic parity analysis",
                severity="low"
            )
        
        # Calculate disparity
        max_rate = max(approval_rates.values())
        min_rate = min(approval_rates.values())
        disparity = max_rate - min_rate
        
        # Calculate fairness score (inverse of disparity)
        fairness_score = 1.0 - min(disparity, 1.0)
        passed = disparity <= self.max_disparity
        
        # Determine severity
        if disparity > 0.4:
            severity = "critical"
        elif disparity > 0.3:
            severity = "high"
        elif disparity > 0.2:
            severity = "medium"
        else:
            severity = "low"
        
        # Generate recommendation
        if passed:
            recommendation = (
                f"Demographic parity acceptable: "
                f"max disparity {disparity:.1%} within threshold {self.max_disparity:.1%}"
            )
        else:
            max_group = max(approval_rates, key=approval_rates.get)
            min_group = min(approval_rates, key=approval_rates.get)
            recommendation = (
                f"PARITY VIOLATION: Approval rate disparity of {disparity:.1%} "
                f"exceeds threshold of {self.max_disparity:.1%}. "
                f"Group '{max_group}' has {max_rate:.1%} approval vs "
                f"'{min_group}' with {min_rate:.1%}. "
                f"Investigate for systemic bias."
            )
        
        return FairnessTestResult(
            test_name="Demographic Parity",
            passed=passed,
            fairness_score=fairness_score,
            details={
                "approval_rates": approval_rates,
                "disparity": disparity,
                "max_rate": max_rate,
                "min_rate": min_rate,
                "threshold": self.max_disparity
            },
            recommendation=recommendation,
            severity=severity
        )


class IndividualFairnessTester:
    """
    Test individual fairness.
    
    Principle: Similar individuals should receive similar decisions.
    
    Uses distance metrics to determine similarity and checks if
    similar cases get similar outcomes.
    """
    
    def __init__(self, similarity_threshold: float = 0.9):
        """
        Initialize individual fairness tester.
        
        Args:
            similarity_threshold: How similar cases must be (0-1)
        """
        self.similarity_threshold = similarity_threshold
    
    def calculate_similarity(
        self,
        case1: Dict[str, Any],
        case2: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate similarity between two cases.
        
        Args:
            case1: First case data
            case2: Second case data
            weights: Optional weights for each field
            
        Returns:
            Similarity score 0-1 (1 = identical)
        """
        if weights is None:
            weights = {}
        
        # Get common fields
        common_fields = set(case1.keys()) & set(case2.keys())
        
        if not common_fields:
            return 0.0
        
        # Calculate weighted similarity
        total_weight = 0.0
        weighted_similarity = 0.0
        
        for field in common_fields:
            weight = weights.get(field, 1.0)
            total_weight += weight
            
            val1 = case1[field]
            val2 = case2[field]
            
            # Calculate field similarity
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Numeric: use normalized difference
                max_val = max(abs(val1), abs(val2), 1)
                field_sim = 1.0 - (abs(val1 - val2) / max_val)
            elif val1 == val2:
                # Exact match
                field_sim = 1.0
            else:
                # Different values
                field_sim = 0.0
            
            weighted_similarity += weight * field_sim
        
        return weighted_similarity / total_weight if total_weight > 0 else 0.0
    
    def test_fairness(
        self,
        cases_with_decisions: List[tuple[Dict[str, Any], str]],
        weights: Optional[Dict[str, float]] = None
    ) -> FairnessTestResult:
        """
        Test individual fairness across cases.
        
        Args:
            cases_with_decisions: List of (case_data, decision) tuples
            weights: Optional field weights for similarity
            
        Returns:
            FairnessTestResult
        """
        logger.info(f"Testing individual fairness for {len(cases_with_decisions)} cases")
        
        violations = []
        total_comparisons = 0
        fair_comparisons = 0
        
        # Compare all pairs
        for i, (case1, decision1) in enumerate(cases_with_decisions):
            for j, (case2, decision2) in enumerate(cases_with_decisions):
                if i >= j:  # Avoid duplicate comparisons
                    continue
                
                similarity = self.calculate_similarity(case1, case2, weights)
                
                if similarity >= self.similarity_threshold:
                    total_comparisons += 1
                    
                    if decision1 == decision2:
                        fair_comparisons += 1
                    else:
                        violations.append({
                            "case1_index": i,
                            "case2_index": j,
                            "similarity": similarity,
                            "decision1": decision1,
                            "decision2": decision2
                        })
        
        # Calculate fairness score
        fairness_score = (
            fair_comparisons / total_comparisons
            if total_comparisons > 0 else 1.0
        )
        passed = fairness_score >= 0.9  # 90% threshold
        
        # Determine severity
        if fairness_score < 0.7:
            severity = "high"
        elif fairness_score < 0.9:
            severity = "medium"
        else:
            severity = "low"
        
        # Generate recommendation
        if passed:
            recommendation = "Individual fairness test passed"
        else:
            recommendation = (
                f"INDIVIDUAL FAIRNESS VIOLATION: "
                f"{len(violations)} similar cases received different decisions. "
                f"Review decision consistency."
            )
        
        return FairnessTestResult(
            test_name="Individual Fairness",
            passed=passed,
            fairness_score=fairness_score,
            details={
                "total_comparisons": total_comparisons,
                "fair_comparisons": fair_comparisons,
                "violations": violations[:10],  # Limit to first 10
                "similarity_threshold": self.similarity_threshold
            },
            recommendation=recommendation,
            severity=severity
        )


# Convenience functions

def get_fairness_tester(test_type: str = "counterfactual", **kwargs):
    """
    Factory function to get fairness tester.
    
    Args:
        test_type: Type of fairness test
        **kwargs: Test-specific configuration
        
    Returns:
        Fairness tester instance
    """
    if test_type == "counterfactual":
        return CounterfactualFairnessTester(**kwargs)
    elif test_type == "demographic_parity":
        return DemographicParityAnalyzer(**kwargs)
    elif test_type == "individual":
        return IndividualFairnessTester(**kwargs)
    else:
        raise ValueError(f"Unknown fairness test type: {test_type}")

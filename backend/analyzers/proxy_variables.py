"""
Proxy Variables Analyzer for TrustChain.

Detects indirect indicators of protected characteristics that could
lead to discriminatory decisions. While protected_attributes.py catches
direct mentions like "race" or "gender", this analyzer catches proxies.

Examples of proxy variables:
- ZIP code → Can proxy for race/ethnicity
- First name → Can proxy for gender/ethnicity
- University name → Can proxy for socioeconomic status
- "Culture fit" → Can proxy for protected characteristics
- "Communication style" → Can proxy for national origin

This is critical because bias often hides behind neutral-sounding variables.

Built with care by Kareem & Claude
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set

from core.base import BaseAnalyzer
from core.registry import register_component
from core.result import StrategyResult, AnalysisResult

logger = logging.getLogger(__name__)


# Proxy variable definitions with risk levels
PROXY_VARIABLES: Dict[str, Dict[str, Any]] = {
    # Location proxies (can indicate race, ethnicity, socioeconomic status)
    "zip_code": {
        "keywords": ["zip code", "zip", "postal code", "neighborhood", "area code", "district"],
        "proxies_for": ["race", "ethnicity", "socioeconomic_status"],
        "risk_level": "high",
        "explanation": "ZIP codes and neighborhoods often correlate with racial demographics"
    },
    "address": {
        "keywords": ["address", "street", "location", "region", "county"],
        "proxies_for": ["race", "ethnicity", "socioeconomic_status"],
        "risk_level": "medium",
        "explanation": "Geographic location can be a proxy for protected characteristics"
    },

    # Name proxies (can indicate gender, ethnicity, national origin)
    "first_name": {
        "keywords": ["first name", "given name", "name sounds", "name suggests"],
        "proxies_for": ["gender", "ethnicity", "national_origin"],
        "risk_level": "high",
        "explanation": "Names can indicate gender and ethnic background"
    },
    "surname": {
        "keywords": ["last name", "surname", "family name"],
        "proxies_for": ["ethnicity", "national_origin"],
        "risk_level": "high",
        "explanation": "Surnames can indicate ethnic or national origin"
    },

    # Education proxies (can indicate socioeconomic status, age)
    "university_prestige": {
        "keywords": ["top school", "elite university", "ivy league", "prestigious", "tier 1", "ranked school"],
        "proxies_for": ["socioeconomic_status", "race"],
        "risk_level": "medium",
        "explanation": "Elite university attendance correlates with socioeconomic background"
    },
    "graduation_year": {
        "keywords": ["graduation year", "graduated in", "class of", "years since graduation"],
        "proxies_for": ["age"],
        "risk_level": "high",
        "explanation": "Graduation year directly indicates approximate age"
    },

    # Work history proxies
    "employment_gaps": {
        "keywords": ["employment gap", "career break", "time off", "gap in resume", "hiatus"],
        "proxies_for": ["gender", "disability", "pregnancy"],
        "risk_level": "high",
        "explanation": "Employment gaps often affect women (caregiving) and disabled individuals disproportionately"
    },
    "years_of_experience": {
        "keywords": ["years of experience", "years in field", "veteran of", "decades of"],
        "proxies_for": ["age"],
        "risk_level": "medium",
        "explanation": "Years of experience correlates directly with age"
    },

    # Cultural/behavioral proxies
    "culture_fit": {
        "keywords": ["culture fit", "cultural fit", "team fit", "fits our culture", "not a fit"],
        "proxies_for": ["race", "ethnicity", "gender", "age"],
        "risk_level": "critical",
        "explanation": "'Culture fit' is frequently used to mask discrimination"
    },
    "communication_style": {
        "keywords": ["communication style", "accent", "articulate", "well-spoken", "professional demeanor"],
        "proxies_for": ["national_origin", "race", "ethnicity"],
        "risk_level": "high",
        "explanation": "Communication style assessments can discriminate against non-native speakers"
    },
    "professionalism": {
        "keywords": ["professional appearance", "grooming", "presentation", "looks professional"],
        "proxies_for": ["race", "gender", "religion"],
        "risk_level": "high",
        "explanation": "Professionalism standards often reflect cultural biases"
    },

    # Financial proxies (for lending/benefits)
    "bank_account_type": {
        "keywords": ["banking history", "bank relationship", "account type", "unbanked"],
        "proxies_for": ["race", "socioeconomic_status"],
        "risk_level": "medium",
        "explanation": "Banking access correlates with racial and economic demographics"
    },
    "credit_history_length": {
        "keywords": ["credit history", "thin file", "limited credit", "no credit history"],
        "proxies_for": ["age", "national_origin", "socioeconomic_status"],
        "risk_level": "medium",
        "explanation": "Credit history length disadvantages younger and immigrant applicants"
    },

    # Social proxies
    "marital_status": {
        "keywords": ["married", "single", "divorced", "widowed", "spouse", "partner"],
        "proxies_for": ["gender", "sexual_orientation"],
        "risk_level": "medium",
        "explanation": "Marital status can proxy for gender and family status"
    },
    "family_obligations": {
        "keywords": ["children", "dependents", "caregiver", "family responsibilities", "childcare"],
        "proxies_for": ["gender", "pregnancy"],
        "risk_level": "high",
        "explanation": "Family obligation questions disproportionately affect women"
    },
    "military_service": {
        "keywords": ["military", "army", "navy", "veteran", "service member", "deployment"],
        "proxies_for": ["veteran_status"],
        "risk_level": "medium",
        "explanation": "While veteran status is sometimes protected, bias can occur"
    },
}


@register_component
class ProxyVariablesAnalyzer(BaseAnalyzer):
    """
    Analyzer that detects proxy variables for protected characteristics.

    Goes beyond direct protected attribute detection to find indirect
    indicators that could lead to discriminatory decisions.

    Configuration options:
        sensitivity: 'low', 'medium', 'high' (default: medium)
        flag_critical_only: Only flag critical-risk proxies (default: False)
        custom_proxies: Additional proxy definitions to check

    Example:
        analyzer = ProxyVariablesAnalyzer(config={
            "sensitivity": "high",
            "flag_critical_only": False
        })
    """

    name = "proxy_variables"
    description = "Detect indirect indicators of protected characteristics"
    version = "1.0.0"
    blocking = True

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize proxy variables analyzer."""
        super().__init__(config)

        self.sensitivity = self.config.get("sensitivity", "medium")
        self.flag_critical_only = self.config.get("flag_critical_only", False)
        self.custom_proxies = self.config.get("custom_proxies", {})

        # Combine built-in and custom proxies
        self.proxy_definitions = {**PROXY_VARIABLES, **self.custom_proxies}

        logger.info(
            f"ProxyVariablesAnalyzer initialized: "
            f"sensitivity={self.sensitivity}, "
            f"{len(self.proxy_definitions)} proxy patterns"
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate analyzer configuration."""
        valid_sensitivities = ["low", "medium", "high"]
        if "sensitivity" in config and config["sensitivity"] not in valid_sensitivities:
            raise ValueError(f"sensitivity must be one of: {valid_sensitivities}")
        return True

    def analyze(
        self,
        strategy_result: StrategyResult,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AnalysisResult:
        """
        Analyze for proxy variable usage.

        Args:
            strategy_result: Output from evaluation strategy
            input_data: Original case data
            context: Policy context

        Returns:
            AnalysisResult with proxy detection findings
        """
        logger.info("Running proxy variables analysis...")

        detected_proxies: List[Dict[str, Any]] = []
        flags: List[str] = []
        warnings: List[str] = []

        # Collect all text to analyze
        text_to_analyze = self._collect_text(strategy_result, input_data)

        # Check each proxy pattern
        for proxy_name, proxy_def in self.proxy_definitions.items():
            matches = self._check_proxy(text_to_analyze, proxy_def)

            if matches:
                risk_level = proxy_def.get("risk_level", "medium")

                # Apply sensitivity filter
                if self._should_flag(risk_level):
                    detected_proxies.append({
                        "proxy": proxy_name,
                        "matched_keywords": matches,
                        "proxies_for": proxy_def.get("proxies_for", []),
                        "risk_level": risk_level,
                        "explanation": proxy_def.get("explanation", ""),
                    })

                    # Generate flag or warning based on risk
                    message = (
                        f"Proxy variable '{proxy_name}' detected (keywords: {', '.join(matches)}). "
                        f"May proxy for: {', '.join(proxy_def.get('proxies_for', []))}. "
                        f"Risk: {risk_level.upper()}"
                    )

                    if risk_level == "critical" or (risk_level == "high" and self.sensitivity == "high"):
                        flags.append(message)
                    else:
                        warnings.append(message)

        # Determine if analysis passed
        passed = len(flags) == 0 or (self.flag_critical_only and not any(
            p["risk_level"] == "critical" for p in detected_proxies
        ))

        # Generate recommendation
        recommendation = self._generate_recommendation(detected_proxies, flags)

        # Build proxy names list for result
        proxy_names = [p["proxy"] for p in detected_proxies]

        result = AnalysisResult(
            analyzer_name=self.name,
            passed=passed,
            flags=flags,
            warnings=warnings,
            details={
                "detected_proxies": detected_proxies,
                "sensitivity": self.sensitivity,
                "total_checked": len(self.proxy_definitions),
            },
            recommendation=recommendation,
            detected_attributes=[],  # Not direct attributes
            detected_proxies=proxy_names,
        )

        if detected_proxies:
            logger.warning(
                f"Detected {len(detected_proxies)} proxy variables: "
                f"{', '.join(proxy_names)}"
            )
        else:
            logger.info("No proxy variables detected")

        return result

    def _collect_text(self, strategy_result: StrategyResult, input_data: Dict[str, Any]) -> str:
        """Collect all text to analyze for proxies."""
        text_parts = []

        # Strategy reasoning
        text_parts.append(strategy_result.reasoning)

        # Model decisions
        for decision in strategy_result.model_decisions:
            if isinstance(decision, dict):
                text_parts.append(decision.get("reasoning", ""))
            elif hasattr(decision, "reasoning"):
                text_parts.append(decision.reasoning)

        # Dissenting views
        text_parts.extend(strategy_result.dissenting_views)

        # Criteria scores (if present)
        for crit_name, crit_data in strategy_result.criteria_scores.items():
            if isinstance(crit_data, dict):
                text_parts.append(crit_data.get("reasoning", ""))

        # Input data keys and values (to catch if decisions reference proxy fields)
        for key, value in input_data.items():
            text_parts.append(str(key))
            text_parts.append(str(value))

        return " ".join(text_parts).lower()

    def _check_proxy(self, text: str, proxy_def: Dict[str, Any]) -> List[str]:
        """Check if any keywords from proxy definition appear in text."""
        matches = []
        for keyword in proxy_def.get("keywords", []):
            if keyword.lower() in text:
                matches.append(keyword)
        return matches

    def _should_flag(self, risk_level: str) -> bool:
        """Determine if a risk level should be flagged based on sensitivity."""
        if self.flag_critical_only:
            return risk_level == "critical"

        risk_hierarchy = {
            "low": ["critical", "high", "medium", "low"],
            "medium": ["critical", "high", "medium"],
            "high": ["critical", "high"],
        }

        flaggable = risk_hierarchy.get(self.sensitivity, ["critical", "high", "medium"])
        return risk_level in flaggable

    def _generate_recommendation(
        self,
        detected_proxies: List[Dict[str, Any]],
        flags: List[str]
    ) -> str:
        """Generate recommendation based on findings."""
        if not detected_proxies:
            return "No proxy variables detected. Decision appears free of indirect discrimination indicators."

        critical_proxies = [p for p in detected_proxies if p["risk_level"] == "critical"]
        high_proxies = [p for p in detected_proxies if p["risk_level"] == "high"]

        recommendations = []

        if critical_proxies:
            recommendations.append(
                f"CRITICAL: {len(critical_proxies)} critical-risk proxy variable(s) detected. "
                f"These strongly suggest potential discrimination. Review decision carefully."
            )
            for p in critical_proxies:
                recommendations.append(f"  - {p['proxy']}: {p['explanation']}")

        if high_proxies:
            recommendations.append(
                f"HIGH RISK: {len(high_proxies)} high-risk proxy variable(s) detected. "
                f"Verify decision is not influenced by these factors."
            )

        if not flags:
            recommendations.append(
                "Proxy variables detected but at acceptable risk levels. "
                "Monitor for patterns across decisions."
            )

        return " ".join(recommendations)

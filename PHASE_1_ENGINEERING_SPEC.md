# TrustChain Phase 1: Core Abstractions Engineering Spec

**Purpose**: This document provides full context for refactoring TrustChain into a modular accountability framework. Hand this to your AI coding assistant or engineering team.

**Author**: Kareem Primo + Claude (November 2025)

---

## What TrustChain Is

TrustChain is an AI accountability framework that makes any AI decision auditable, explainable, and fair. Originally built for multi-model consensus on government benefits decisions, it's evolving into a modular toolkit that works with:

- Multiple AI models (consensus-based)
- Single AI models (alternative accountability methods)
- Any decision type (hiring, lending, benefits, content moderation, etc.)

**Core Value Prop**: "TrustChain makes any AI accountable - whether you're using one model or five. Same audit trail. Same explainability. Same bias protection."

---

## Current Architecture (What Exists)

```
TrustChain/backend/
├── app.py                    # FastAPI endpoints
├── providers/                # AI provider integrations
│   ├── base.py              # BaseLLMProvider abstract class
│   ├── anthropic_provider.py
│   ├── openai_provider.py
│   ├── llama_provider.py
│   └── registry.py          # Provider registration
├── services/
│   ├── orchestrator.py      # Main decision coordinator
│   ├── bias_detection.py    # Keyword-based bias scanning
│   ├── consensus_algorithms.py  # Weighted voting
│   └── safety_monitor.py
├── models/
│   └── decision.py          # Data models (Decision, ModelDecision, etc.)
└── database/
    └── ...                   # SQLite/Postgres storage
```

**What works well:**
- Multi-model parallel execution via asyncio
- Basic bias detection (protected attribute keywords)
- Audit trail with SHA-256 hashing
- Weighted consensus calculation
- Clean provider abstraction

**What's limited:**
- Hard-coded to multi-model consensus only
- Bias detection is keyword-only (misses proxy variables)
- No consumer-facing explanation output
- No single-model accountability strategies
- Tightly coupled - can't mix and match components

---

## Target Architecture (What We're Building)

```
TrustChain/backend/
├── app.py
├── core/                          # NEW: Core abstractions
│   ├── __init__.py
│   ├── base.py                    # Abstract base classes
│   ├── registry.py                # Plugin registration system
│   ├── config.py                  # Configuration loader
│   └── result.py                  # AccountabilityResult unified output
│
├── strategies/                    # NEW: Evaluation strategies (pick one or combine)
│   ├── __init__.py
│   ├── base.py                    # BaseStrategy abstract class
│   ├── multi_model_consensus.py   # Existing, refactored
│   ├── criteria_decomposition.py  # NEW
│   ├── adversarial_review.py      # NEW
│   ├── multi_pass.py              # NEW
│   ├── constitutional_check.py    # NEW
│   └── historical_consistency.py  # NEW
│
├── analyzers/                     # NEW: Analysis modules (stack as needed)
│   ├── __init__.py
│   ├── base.py                    # BaseAnalyzer abstract class
│   ├── protected_attributes.py    # Existing, refactored
│   ├── proxy_variables.py         # NEW
│   ├── confidence_calibration.py  # NEW
│   ├── reasoning_quality.py       # NEW
│   ├── gap_analysis.py            # NEW
│   └── outcome_patterns.py        # NEW (requires historical data)
│
├── outputs/                       # NEW: Output generators (format for audience)
│   ├── __init__.py
│   ├── base.py                    # BaseOutput abstract class
│   ├── internal_audit.py          # Existing, refactored
│   ├── consumer_explanation.py    # NEW
│   ├── compliance_report.py       # NEW
│   ├── training_signal.py         # NEW
│   └── appeal_package.py          # NEW
│
├── providers/                     # KEEP: AI provider integrations
│   └── ... (unchanged)
│
├── services/
│   ├── orchestrator.py            # REFACTOR: Uses new plugin system
│   └── trustchain.py              # NEW: Main entry point
│
├── models/
│   └── decision.py                # EXTEND: Add new result types
│
└── database/
    └── ...
```

---

## Phase 1 Deliverables: Core Abstractions

Phase 1 establishes the plugin architecture. After this, all subsequent features plug in cleanly.

### 1.1 Base Classes (`core/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum

class ComponentType(str, Enum):
    """Types of pluggable components."""
    STRATEGY = "strategy"
    ANALYZER = "analyzer"
    OUTPUT = "output"


class BaseComponent(ABC):
    """Base class for all pluggable TrustChain components."""
    
    component_type: ComponentType
    name: str
    description: str
    version: str = "1.0.0"
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate component configuration."""
        pass
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Return component metadata for registry."""
        return {
            "name": self.name,
            "type": self.component_type.value,
            "description": self.description,
            "version": self.version
        }


class BaseStrategy(BaseComponent):
    """
    Base class for evaluation strategies.
    
    Strategies determine HOW accountability is established:
    - Multi-model consensus
    - Single-model with multiple passes
    - Criteria decomposition
    - Adversarial self-review
    - etc.
    """
    
    component_type = ComponentType.STRATEGY
    
    @abstractmethod
    async def evaluate(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        providers: List[Any]  # List of LLM providers
    ) -> "StrategyResult":
        """
        Execute the evaluation strategy.
        
        Args:
            input_data: The case/application data to evaluate
            context: Policy context, criteria, principles, etc.
            providers: Available LLM providers (may be one or many)
            
        Returns:
            StrategyResult with decision, reasoning, confidence, etc.
        """
        pass


class BaseAnalyzer(BaseComponent):
    """
    Base class for analysis modules.
    
    Analyzers examine evaluation results for issues:
    - Bias detection (protected attributes, proxies)
    - Confidence calibration
    - Reasoning quality
    - Gap analysis
    - etc.
    """
    
    component_type = ComponentType.ANALYZER
    
    @abstractmethod
    def analyze(
        self,
        strategy_result: "StrategyResult",
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> "AnalysisResult":
        """
        Analyze the strategy result for issues.
        
        Args:
            strategy_result: Output from evaluation strategy
            input_data: Original case data
            context: Policy context
            
        Returns:
            AnalysisResult with findings, flags, recommendations
        """
        pass


class BaseOutput(BaseComponent):
    """
    Base class for output generators.
    
    Outputs format results for specific audiences:
    - Internal audit logs
    - Consumer-facing explanations
    - Compliance reports
    - Training signals
    - etc.
    """
    
    component_type = ComponentType.OUTPUT
    
    @abstractmethod
    def generate(
        self,
        accountability_result: "AccountabilityResult"
    ) -> Any:
        """
        Generate formatted output.
        
        Args:
            accountability_result: Complete result from TrustChain
            
        Returns:
            Formatted output (dict, string, object depending on type)
        """
        pass
```

### 1.2 Result Objects (`core/result.py`)

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import hashlib
import json


class DecisionOutcome(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    NEEDS_REVIEW = "needs_review"
    ESCALATE = "escalate"
    INSUFFICIENT_DATA = "insufficient_data"


class ReviewTrigger(str, Enum):
    """Reasons a decision requires human review."""
    LOW_CONFIDENCE = "low_confidence"
    BIAS_DETECTED = "bias_detected"
    PROXY_DETECTED = "proxy_detected"
    CONSENSUS_DISAGREEMENT = "consensus_disagreement"
    HIGH_STAKES_DECISION = "high_stakes_decision"
    REASONING_DIVERGENCE = "reasoning_divergence"
    POLICY_VIOLATION = "policy_violation"
    ADVERSARIAL_CHALLENGE_SUCCEEDED = "adversarial_challenge_succeeded"


@dataclass
class StrategyResult:
    """Output from an evaluation strategy."""
    
    strategy_name: str
    decision: DecisionOutcome
    confidence: float  # 0.0 - 1.0
    reasoning: str
    
    # For multi-model strategies
    model_decisions: List[Dict[str, Any]] = field(default_factory=list)
    agreement_level: Optional[float] = None
    dissenting_views: List[str] = field(default_factory=list)
    
    # For criteria decomposition
    criteria_scores: Dict[str, Any] = field(default_factory=dict)
    
    # For adversarial review
    challenges: List[Dict[str, Any]] = field(default_factory=list)
    challenge_survived: bool = True
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    latency_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    raw_responses: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Output from an analyzer module."""
    
    analyzer_name: str
    passed: bool  # Did it pass this analysis?
    
    flags: List[str] = field(default_factory=list)  # Issues found
    warnings: List[str] = field(default_factory=list)  # Concerns but not blockers
    
    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: Optional[str] = None
    
    # For bias detection
    detected_attributes: List[str] = field(default_factory=list)
    detected_proxies: List[str] = field(default_factory=list)
    
    # For gap analysis
    matched_criteria: List[str] = field(default_factory=list)
    missing_criteria: List[str] = field(default_factory=list)
    partial_criteria: List[str] = field(default_factory=list)


@dataclass
class AccountabilityResult:
    """
    Complete output from TrustChain.
    
    This is the unified result object that all components contribute to.
    """
    
    # Identification
    result_id: str
    case_id: str
    decision_type: str
    
    # Core decision
    final_decision: DecisionOutcome
    overall_confidence: float
    requires_human_review: bool
    review_triggers: List[ReviewTrigger] = field(default_factory=list)
    
    # Component outputs
    strategy_result: Optional[StrategyResult] = None
    analysis_results: List[AnalysisResult] = field(default_factory=list)
    
    # Explainability
    primary_reasoning: str = ""
    supporting_factors: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    
    # For consumer explanation
    consumer_summary: Optional[str] = None
    feedback_points: List[Dict[str, Any]] = field(default_factory=list)
    
    # Audit trail
    input_data_hash: str = ""  # Hash of input for integrity
    audit_hash: str = ""  # Hash of entire result
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Configuration used
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_audit_hash(self) -> str:
        """Generate tamper-evident hash of the result."""
        hash_content = {
            "result_id": self.result_id,
            "case_id": self.case_id,
            "final_decision": self.final_decision.value,
            "confidence": self.overall_confidence,
            "timestamp": self.timestamp.isoformat(),
            "reasoning": self.primary_reasoning
        }
        return hashlib.sha256(
            json.dumps(hash_content, sort_keys=True).encode()
        ).hexdigest()
    
    def finalize(self) -> "AccountabilityResult":
        """Lock the result and generate audit hash."""
        self.audit_hash = self.calculate_audit_hash()
        return self
```

### 1.3 Plugin Registry (`core/registry.py`)

```python
from typing import Any, Dict, List, Optional, Type
from .base import BaseComponent, BaseStrategy, BaseAnalyzer, BaseOutput, ComponentType
import logging

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """
    Registry for TrustChain plugins.
    
    Allows dynamic registration and discovery of:
    - Evaluation strategies
    - Analysis modules  
    - Output generators
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._strategies: Dict[str, Type[BaseStrategy]] = {}
            cls._instance._analyzers: Dict[str, Type[BaseAnalyzer]] = {}
            cls._instance._outputs: Dict[str, Type[BaseOutput]] = {}
        return cls._instance
    
    def register(self, component_class: Type[BaseComponent]) -> None:
        """Register a component class."""
        instance = component_class()
        name = instance.name
        
        if instance.component_type == ComponentType.STRATEGY:
            self._strategies[name] = component_class
            logger.info(f"Registered strategy: {name}")
            
        elif instance.component_type == ComponentType.ANALYZER:
            self._analyzers[name] = component_class
            logger.info(f"Registered analyzer: {name}")
            
        elif instance.component_type == ComponentType.OUTPUT:
            self._outputs[name] = component_class
            logger.info(f"Registered output: {name}")
    
    def get_strategy(self, name: str, config: Dict[str, Any] = None) -> BaseStrategy:
        """Get an instance of a registered strategy."""
        if name not in self._strategies:
            raise ValueError(f"Unknown strategy: {name}. Available: {list(self._strategies.keys())}")
        return self._strategies[name](config or {})
    
    def get_analyzer(self, name: str, config: Dict[str, Any] = None) -> BaseAnalyzer:
        """Get an instance of a registered analyzer."""
        if name not in self._analyzers:
            raise ValueError(f"Unknown analyzer: {name}. Available: {list(self._analyzers.keys())}")
        return self._analyzers[name](config or {})
    
    def get_output(self, name: str, config: Dict[str, Any] = None) -> BaseOutput:
        """Get an instance of a registered output generator."""
        if name not in self._outputs:
            raise ValueError(f"Unknown output: {name}. Available: {list(self._outputs.keys())}")
        return self._outputs[name](config or {})
    
    def list_components(self) -> Dict[str, List[str]]:
        """List all registered components."""
        return {
            "strategies": list(self._strategies.keys()),
            "analyzers": list(self._analyzers.keys()),
            "outputs": list(self._outputs.keys())
        }


# Decorator for easy registration
def register_component(cls: Type[BaseComponent]) -> Type[BaseComponent]:
    """Decorator to register a component."""
    ComponentRegistry().register(cls)
    return cls


# Global registry instance
def get_registry() -> ComponentRegistry:
    return ComponentRegistry()
```

### 1.4 Configuration System (`core/config.py`)

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import yaml
import json


@dataclass
class StrategyConfig:
    """Configuration for an evaluation strategy."""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class AnalyzerConfig:
    """Configuration for an analyzer module."""
    name: str
    enabled: bool = True
    blocking: bool = True  # If True, failures require review
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputConfig:
    """Configuration for an output generator."""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrustChainConfig:
    """
    Complete TrustChain configuration.
    
    Example YAML:
    
    ```yaml
    decision_type: "hiring"
    
    strategies:
      - name: "criteria_decomposition"
        config:
          criteria:
            - "experience_requirement"
            - "skills_requirement"
            - "education_requirement"
      - name: "adversarial_review"
        config:
          challenge_strength: "medium"
    
    analyzers:
      - name: "protected_attributes"
        blocking: true
      - name: "proxy_variables"
        blocking: true
        config:
          sensitivity: "high"
      - name: "gap_analysis"
        blocking: false
    
    outputs:
      - name: "consumer_explanation"
      - name: "internal_audit"
    
    thresholds:
      min_confidence: 0.7
      auto_approve_threshold: 0.9
      auto_deny_threshold: 0.1
    ```
    """
    
    decision_type: str
    strategies: List[StrategyConfig] = field(default_factory=list)
    analyzers: List[AnalyzerConfig] = field(default_factory=list)
    outputs: List[OutputConfig] = field(default_factory=list)
    
    # Decision thresholds
    min_confidence: float = 0.7
    auto_approve_threshold: float = 0.9
    auto_deny_threshold: float = 0.1
    
    # Behavior flags
    require_all_strategies: bool = False  # If True, all strategies must agree
    fail_open: bool = False  # If True, errors result in approval (dangerous!)
    
    @classmethod
    def from_yaml(cls, path: str) -> "TrustChainConfig":
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls._from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustChainConfig":
        """Load configuration from dictionary."""
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "TrustChainConfig":
        strategies = [
            StrategyConfig(**s) for s in data.get("strategies", [])
        ]
        analyzers = [
            AnalyzerConfig(**a) for a in data.get("analyzers", [])
        ]
        outputs = [
            OutputConfig(**o) for o in data.get("outputs", [])
        ]
        
        return cls(
            decision_type=data.get("decision_type", "general"),
            strategies=strategies,
            analyzers=analyzers,
            outputs=outputs,
            min_confidence=data.get("thresholds", {}).get("min_confidence", 0.7),
            auto_approve_threshold=data.get("thresholds", {}).get("auto_approve_threshold", 0.9),
            auto_deny_threshold=data.get("thresholds", {}).get("auto_deny_threshold", 0.1),
            require_all_strategies=data.get("require_all_strategies", False),
            fail_open=data.get("fail_open", False)
        )
```

### 1.5 Main TrustChain Service (`services/trustchain.py`)

```python
"""
TrustChain Main Service

This is the primary entry point for the TrustChain framework.
It orchestrates strategies, analyzers, and outputs based on configuration.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from core.base import BaseStrategy, BaseAnalyzer, BaseOutput
from core.config import TrustChainConfig
from core.registry import get_registry
from core.result import (
    AccountabilityResult,
    StrategyResult,
    AnalysisResult,
    DecisionOutcome,
    ReviewTrigger
)

logger = logging.getLogger(__name__)


class TrustChain:
    """
    Main TrustChain service.
    
    Usage:
        # From config file
        tc = TrustChain.from_config("configs/hiring.yaml")
        result = await tc.evaluate(case_data, context)
        
        # Programmatic
        tc = TrustChain(
            strategies=[CriteriaDecomposition(), AdversarialReview()],
            analyzers=[ProxyVariableDetection(), GapAnalysis()],
            outputs=[ConsumerExplanation()]
        )
        result = await tc.evaluate(case_data, context)
    """
    
    def __init__(
        self,
        config: Optional[TrustChainConfig] = None,
        strategies: Optional[List[BaseStrategy]] = None,
        analyzers: Optional[List[BaseAnalyzer]] = None,
        outputs: Optional[List[BaseOutput]] = None,
        providers: Optional[List[Any]] = None  # LLM providers
    ):
        self.config = config
        self.registry = get_registry()
        
        # Initialize components from config or direct injection
        if config:
            self.strategies = self._load_strategies(config)
            self.analyzers = self._load_analyzers(config)
            self.outputs = self._load_outputs(config)
        else:
            self.strategies = strategies or []
            self.analyzers = analyzers or []
            self.outputs = outputs or []
        
        self.providers = providers or []
        
        logger.info(
            f"TrustChain initialized: "
            f"{len(self.strategies)} strategies, "
            f"{len(self.analyzers)} analyzers, "
            f"{len(self.outputs)} outputs"
        )
    
    @classmethod
    def from_config(cls, config_path: str, providers: List[Any] = None) -> "TrustChain":
        """Create TrustChain instance from config file."""
        config = TrustChainConfig.from_yaml(config_path)
        return cls(config=config, providers=providers)
    
    def _load_strategies(self, config: TrustChainConfig) -> List[BaseStrategy]:
        """Load strategies from config."""
        strategies = []
        for sc in config.strategies:
            if sc.enabled:
                strategy = self.registry.get_strategy(sc.name, sc.config)
                strategies.append(strategy)
        return strategies
    
    def _load_analyzers(self, config: TrustChainConfig) -> List[BaseAnalyzer]:
        """Load analyzers from config."""
        analyzers = []
        for ac in config.analyzers:
            if ac.enabled:
                analyzer = self.registry.get_analyzer(ac.name, ac.config)
                analyzer._blocking = ac.blocking  # Store blocking flag
                analyzers.append(analyzer)
        return analyzers
    
    def _load_outputs(self, config: TrustChainConfig) -> List[BaseOutput]:
        """Load output generators from config."""
        outputs = []
        for oc in config.outputs:
            if oc.enabled:
                output = self.registry.get_output(oc.name, oc.config)
                outputs.append(output)
        return outputs
    
    async def evaluate(
        self,
        case_id: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AccountabilityResult:
        """
        Run full TrustChain evaluation.
        
        Args:
            case_id: Unique identifier for this case
            input_data: The data to evaluate (application, resume, etc.)
            context: Policy context, criteria, etc.
            
        Returns:
            Complete AccountabilityResult
        """
        context = context or {}
        result_id = f"tc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Starting evaluation: {result_id} for case {case_id}")
        
        # Initialize result
        result = AccountabilityResult(
            result_id=result_id,
            case_id=case_id,
            decision_type=self.config.decision_type if self.config else "general",
            final_decision=DecisionOutcome.NEEDS_REVIEW,
            overall_confidence=0.0,
            requires_human_review=False
        )
        
        # STEP 1: Run evaluation strategies
        logger.info(f"Running {len(self.strategies)} evaluation strategies...")
        strategy_results = []
        
        for strategy in self.strategies:
            try:
                sr = await strategy.evaluate(input_data, context, self.providers)
                strategy_results.append(sr)
                logger.info(f"  {strategy.name}: {sr.decision.value} ({sr.confidence:.0%})")
            except Exception as e:
                logger.error(f"  {strategy.name} failed: {e}")
                if not (self.config and self.config.fail_open):
                    result.review_triggers.append(ReviewTrigger.REASONING_DIVERGENCE)
        
        # Combine strategy results
        result.strategy_result = self._combine_strategy_results(strategy_results)
        
        # STEP 2: Run analyzers
        logger.info(f"Running {len(self.analyzers)} analyzers...")
        
        for analyzer in self.analyzers:
            try:
                ar = analyzer.analyze(result.strategy_result, input_data, context)
                result.analysis_results.append(ar)
                
                status = "✓ passed" if ar.passed else "✗ FLAGGED"
                logger.info(f"  {analyzer.name}: {status}")
                
                # Check if blocking analyzer failed
                if not ar.passed and getattr(analyzer, '_blocking', True):
                    result.requires_human_review = True
                    if ar.detected_attributes:
                        result.review_triggers.append(ReviewTrigger.BIAS_DETECTED)
                    if ar.detected_proxies:
                        result.review_triggers.append(ReviewTrigger.PROXY_DETECTED)
                        
            except Exception as e:
                logger.error(f"  {analyzer.name} failed: {e}")
        
        # STEP 3: Determine final decision
        result = self._determine_final_decision(result)
        
        # STEP 4: Generate outputs
        logger.info(f"Generating {len(self.outputs)} outputs...")
        result = result.finalize()
        
        generated_outputs = {}
        for output in self.outputs:
            try:
                generated_outputs[output.name] = output.generate(result)
            except Exception as e:
                logger.error(f"  {output.name} failed: {e}")
        
        # Store consumer summary if generated
        if "consumer_explanation" in generated_outputs:
            result.consumer_summary = generated_outputs["consumer_explanation"].get("summary")
            result.feedback_points = generated_outputs["consumer_explanation"].get("feedback", [])
        
        logger.info(f"Evaluation complete: {result.final_decision.value} (review: {result.requires_human_review})")
        
        return result
    
    def _combine_strategy_results(self, results: List[StrategyResult]) -> StrategyResult:
        """Combine multiple strategy results into one."""
        if not results:
            return StrategyResult(
                strategy_name="none",
                decision=DecisionOutcome.NEEDS_REVIEW,
                confidence=0.0,
                reasoning="No strategies completed successfully"
            )
        
        if len(results) == 1:
            return results[0]
        
        # Multiple strategies - need to reconcile
        decisions = [r.decision for r in results]
        confidences = [r.confidence for r in results]
        
        # Majority decision
        from collections import Counter
        decision_counts = Counter(decisions)
        majority_decision = decision_counts.most_common(1)[0][0]
        
        # Average confidence
        avg_confidence = sum(confidences) / len(confidences)
        
        # Agreement level
        agreement = decision_counts[majority_decision] / len(decisions)
        
        return StrategyResult(
            strategy_name="combined",
            decision=majority_decision,
            confidence=avg_confidence,
            reasoning=f"Combined result from {len(results)} strategies with {agreement:.0%} agreement",
            agreement_level=agreement,
            dissenting_views=[
                r.reasoning for r in results if r.decision != majority_decision
            ]
        )
    
    def _determine_final_decision(self, result: AccountabilityResult) -> AccountabilityResult:
        """Determine final decision based on strategy results and analysis."""
        sr = result.strategy_result
        
        if not sr:
            result.final_decision = DecisionOutcome.NEEDS_REVIEW
            result.requires_human_review = True
            return result
        
        result.overall_confidence = sr.confidence
        result.primary_reasoning = sr.reasoning
        
        # Check thresholds
        min_conf = self.config.min_confidence if self.config else 0.7
        
        if sr.confidence < min_conf:
            result.requires_human_review = True
            result.review_triggers.append(ReviewTrigger.LOW_CONFIDENCE)
        
        # Check for any review triggers
        if result.review_triggers:
            result.requires_human_review = True
            result.final_decision = DecisionOutcome.NEEDS_REVIEW
        else:
            result.final_decision = sr.decision
        
        return result
```

---

## Phase 1 TODO Checklist

```
[ ] Create /backend/core/ directory
[ ] Implement core/base.py with BaseComponent, BaseStrategy, BaseAnalyzer, BaseOutput
[ ] Implement core/result.py with StrategyResult, AnalysisResult, AccountabilityResult
[ ] Implement core/registry.py with ComponentRegistry and decorators
[ ] Implement core/config.py with TrustChainConfig and YAML loading
[ ] Implement services/trustchain.py main service
[ ] Create /backend/strategies/ directory with __init__.py and base.py
[ ] Create /backend/analyzers/ directory with __init__.py and base.py
[ ] Create /backend/outputs/ directory with __init__.py and base.py
[ ] Refactor existing multi_model_consensus into strategies/multi_model_consensus.py
[ ] Refactor existing bias_detection into analyzers/protected_attributes.py
[ ] Create basic internal_audit output in outputs/internal_audit.py
[ ] Update app.py endpoints to use new TrustChain service
[ ] Add example config YAML files in /configs/ directory
[ ] Write tests for core abstractions
[ ] Update README with new architecture
```

---

## Code Style Guidelines

- Follow existing patterns in the codebase
- Use dataclasses for data containers
- Use async/await for anything that might call LLMs
- Type hints everywhere
- Docstrings with Args/Returns sections
- Logging at INFO level for major steps, DEBUG for details
- Keep the friendly comment style ("Built with 🤝 by Kareem & Claude")

---

## Questions for Implementation

1. Should strategies be able to call other strategies? (composition)
2. Should analyzers be able to see other analyzers' results? (chaining)
3. Do we need versioning for configs to track changes over time?
4. Should there be a "dry run" mode that doesn't call LLMs?

---

## After Phase 1

Once core abstractions are in place, Phase 2-4 features can be built independently:

- **Phase 2**: New evaluation strategies (criteria decomposition, adversarial review, etc.)
- **Phase 3**: New analyzers (proxy variables, reasoning quality, etc.)
- **Phase 4**: New outputs (consumer explanation, compliance report, etc.)

Each new component is just a class that extends the base and registers itself.

---

*Document generated November 2025. TrustChain - Making AI accountable.*

"""
TrustChain Configuration System

Configuration classes for setting up TrustChain evaluations:
- StrategyConfig: Configuration for evaluation strategies
- AnalyzerConfig: Configuration for analyzer modules
- OutputConfig: Configuration for output generators
- TrustChainConfig: Complete configuration for a TrustChain instance

Supports loading from YAML files or dictionaries.

Built with care by Kareem & Claude
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import yaml
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """
    Configuration for an evaluation strategy.

    Attributes:
        name: Name of the strategy (must match registered name)
        enabled: Whether this strategy is active
        config: Strategy-specific configuration options
    """
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyzerConfig:
    """
    Configuration for an analyzer module.

    Attributes:
        name: Name of the analyzer (must match registered name)
        enabled: Whether this analyzer is active
        blocking: If True, analysis failures require human review
        config: Analyzer-specific configuration options
    """
    name: str
    enabled: bool = True
    blocking: bool = True  # If True, failures require review
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputConfig:
    """
    Configuration for an output generator.

    Attributes:
        name: Name of the output generator (must match registered name)
        enabled: Whether this output is active
        config: Output-specific configuration options
    """
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrustChainConfig:
    """
    Complete TrustChain configuration.

    Defines which strategies, analyzers, and outputs to use,
    along with decision thresholds and behavior flags.

    Example YAML configuration:

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

    Attributes:
        decision_type: Type of decision (hiring, benefits, lending, etc.)
        strategies: List of strategy configurations
        analyzers: List of analyzer configurations
        outputs: List of output generator configurations

        # Decision thresholds
        min_confidence: Minimum confidence to auto-decide (default 0.7)
        auto_approve_threshold: Confidence above this auto-approves (default 0.9)
        auto_deny_threshold: Confidence below this auto-denies (default 0.1)

        # Behavior flags
        require_all_strategies: If True, all strategies must agree
        fail_open: If True, errors result in approval (dangerous!)
        human_review_on_error: If True, errors trigger human review
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
    human_review_on_error: bool = True  # If True, errors trigger human review

    @classmethod
    def from_yaml(cls, path: str | Path) -> "TrustChainConfig":
        """
        Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            TrustChainConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        logger.info(f"Loading TrustChain config from: {path}")

        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        return cls._from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustChainConfig":
        """
        Load configuration from a dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            TrustChainConfig instance
        """
        return cls._from_dict(data)

    @classmethod
    def from_json(cls, json_str: str) -> "TrustChainConfig":
        """
        Load configuration from a JSON string.

        Args:
            json_str: JSON configuration string

        Returns:
            TrustChainConfig instance
        """
        data = json.loads(json_str)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "TrustChainConfig":
        """
        Internal method to create config from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            TrustChainConfig instance
        """
        # Parse strategies
        strategies = []
        for s in data.get("strategies", []):
            if isinstance(s, str):
                # Simple form: just the name
                strategies.append(StrategyConfig(name=s))
            else:
                # Full form: dict with name and options
                strategies.append(StrategyConfig(
                    name=s.get("name"),
                    enabled=s.get("enabled", True),
                    config=s.get("config", {}),
                ))

        # Parse analyzers
        analyzers = []
        for a in data.get("analyzers", []):
            if isinstance(a, str):
                analyzers.append(AnalyzerConfig(name=a))
            else:
                analyzers.append(AnalyzerConfig(
                    name=a.get("name"),
                    enabled=a.get("enabled", True),
                    blocking=a.get("blocking", True),
                    config=a.get("config", {}),
                ))

        # Parse outputs
        outputs = []
        for o in data.get("outputs", []):
            if isinstance(o, str):
                outputs.append(OutputConfig(name=o))
            else:
                outputs.append(OutputConfig(
                    name=o.get("name"),
                    enabled=o.get("enabled", True),
                    config=o.get("config", {}),
                ))

        # Parse thresholds (nested under 'thresholds' key)
        thresholds = data.get("thresholds", {})

        return cls(
            decision_type=data.get("decision_type", "general"),
            strategies=strategies,
            analyzers=analyzers,
            outputs=outputs,
            min_confidence=thresholds.get("min_confidence", 0.7),
            auto_approve_threshold=thresholds.get("auto_approve_threshold", 0.9),
            auto_deny_threshold=thresholds.get("auto_deny_threshold", 0.1),
            require_all_strategies=data.get("require_all_strategies", False),
            fail_open=data.get("fail_open", False),
            human_review_on_error=data.get("human_review_on_error", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration as a dictionary
        """
        return {
            "decision_type": self.decision_type,
            "strategies": [
                {
                    "name": s.name,
                    "enabled": s.enabled,
                    "config": s.config,
                }
                for s in self.strategies
            ],
            "analyzers": [
                {
                    "name": a.name,
                    "enabled": a.enabled,
                    "blocking": a.blocking,
                    "config": a.config,
                }
                for a in self.analyzers
            ],
            "outputs": [
                {
                    "name": o.name,
                    "enabled": o.enabled,
                    "config": o.config,
                }
                for o in self.outputs
            ],
            "thresholds": {
                "min_confidence": self.min_confidence,
                "auto_approve_threshold": self.auto_approve_threshold,
                "auto_deny_threshold": self.auto_deny_threshold,
            },
            "require_all_strategies": self.require_all_strategies,
            "fail_open": self.fail_open,
            "human_review_on_error": self.human_review_on_error,
        }

    def to_yaml(self, path: Optional[str | Path] = None) -> str:
        """
        Convert configuration to YAML string, optionally saving to file.

        Args:
            path: Optional path to save the YAML file

        Returns:
            YAML string representation
        """
        yaml_str = yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

        if path:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                f.write(yaml_str)
            logger.info(f"Saved TrustChain config to: {path}")

        return yaml_str

    def validate(self) -> List[str]:
        """
        Validate the configuration.

        Checks for common configuration errors like missing names,
        invalid thresholds, or dangerous settings.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check decision type
        if not self.decision_type:
            errors.append("decision_type is required")

        # Check thresholds
        if not 0 <= self.min_confidence <= 1:
            errors.append("min_confidence must be between 0 and 1")
        if not 0 <= self.auto_approve_threshold <= 1:
            errors.append("auto_approve_threshold must be between 0 and 1")
        if not 0 <= self.auto_deny_threshold <= 1:
            errors.append("auto_deny_threshold must be between 0 and 1")
        if self.auto_deny_threshold >= self.auto_approve_threshold:
            errors.append("auto_deny_threshold must be less than auto_approve_threshold")

        # Warn about dangerous settings
        if self.fail_open:
            errors.append(
                "WARNING: fail_open=True is dangerous - errors will result in approvals"
            )

        # Check strategies have names
        for i, s in enumerate(self.strategies):
            if not s.name:
                errors.append(f"Strategy at index {i} has no name")

        # Check analyzers have names
        for i, a in enumerate(self.analyzers):
            if not a.name:
                errors.append(f"Analyzer at index {i} has no name")

        # Check outputs have names
        for i, o in enumerate(self.outputs):
            if not o.name:
                errors.append(f"Output at index {i} has no name")

        return errors

    def get_enabled_strategies(self) -> List[StrategyConfig]:
        """Get list of enabled strategy configs."""
        return [s for s in self.strategies if s.enabled]

    def get_enabled_analyzers(self) -> List[AnalyzerConfig]:
        """Get list of enabled analyzer configs."""
        return [a for a in self.analyzers if a.enabled]

    def get_enabled_outputs(self) -> List[OutputConfig]:
        """Get list of enabled output configs."""
        return [o for o in self.outputs if o.enabled]

    def get_blocking_analyzers(self) -> List[AnalyzerConfig]:
        """Get list of enabled blocking analyzer configs."""
        return [a for a in self.analyzers if a.enabled and a.blocking]

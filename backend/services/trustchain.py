"""
TrustChain Main Service

This is the primary entry point for the TrustChain accountability framework.
It orchestrates strategies, analyzers, and outputs based on configuration.

Usage:
    # From config file
    tc = TrustChain.from_config("configs/hiring.yaml")
    result = await tc.evaluate(case_id, input_data, context)

    # Programmatic
    tc = TrustChain(
        strategies=[MultiModelConsensusStrategy()],
        analyzers=[ProtectedAttributesAnalyzer()],
        outputs=[InternalAuditOutput()]
    )
    result = await tc.evaluate(case_id, input_data, context)

    # With learned parameters (Phase 3)
    from learning import LearningEngine, get_feedback_store
    engine = LearningEngine(get_feedback_store())
    params = engine.get_parameters("hiring")
    tc = TrustChain.from_config("configs/hiring.yaml", learned_parameters=params)

Built with care by Kareem & Claude
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import hashlib
import json

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

    Coordinates evaluation strategies, analysis modules, and output generators
    to produce accountable AI decisions with full audit trails.

    The TrustChain service:
    1. Loads components from config or accepts direct injection
    2. Runs evaluation strategies to get initial decisions
    3. Runs analyzers to check for bias and other issues
    4. Determines final decision based on results and thresholds
    5. Generates formatted outputs for different audiences
    6. Returns complete AccountabilityResult with audit hash

    Attributes:
        config: TrustChainConfig instance (if loaded from file)
        strategies: List of evaluation strategy instances
        analyzers: List of analyzer instances
        outputs: List of output generator instances
        providers: List of LLM provider instances
    """

    def __init__(
        self,
        config: Optional[TrustChainConfig] = None,
        strategies: Optional[List[BaseStrategy]] = None,
        analyzers: Optional[List[BaseAnalyzer]] = None,
        outputs: Optional[List[BaseOutput]] = None,
        providers: Optional[List[Any]] = None,
        learned_parameters: Optional[Any] = None,  # LearnedParameters from learning module
        enable_counterfactual_testing: bool = False  # Phase 5: Counterfactual fairness
    ):
        """
        Initialize TrustChain service.

        Args:
            config: Configuration object (loads components from registry)
            strategies: Direct list of strategy instances
            analyzers: Direct list of analyzer instances
            outputs: Direct list of output generator instances
            providers: List of LLM provider instances
            learned_parameters: LearnedParameters from feedback learning engine
            enable_counterfactual_testing: If True, adds CounterfactualFairnessAnalyzer
        """
        self.config = config
        self.registry = get_registry()
        self.learned_parameters = learned_parameters
        self.enable_counterfactual_testing = enable_counterfactual_testing

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

        # Apply learned parameters if provided
        if learned_parameters:
            self._apply_learned_parameters(learned_parameters)

        # Phase 5: Add counterfactual testing analyzer if enabled
        if enable_counterfactual_testing:
            from analyzers.counterfactual_fairness import CounterfactualFairnessAnalyzer
            cf_analyzer = CounterfactualFairnessAnalyzer()
            cf_analyzer._blocking = True  # Bias detection blocks automated decisions
            self.analyzers.append(cf_analyzer)
            logger.info("Counterfactual fairness testing enabled")

        logger.info(
            f"TrustChain initialized: "
            f"{len(self.strategies)} strategies, "
            f"{len(self.analyzers)} analyzers, "
            f"{len(self.outputs)} outputs, "
            f"{len(self.providers)} providers"
            + (", with learned parameters" if learned_parameters else "")
            + (", with counterfactual testing" if enable_counterfactual_testing else "")
        )

    @classmethod
    def from_config(
        cls,
        config_path: str,
        providers: Optional[List[Any]] = None,
        learned_parameters: Optional[Any] = None
    ) -> "TrustChain":
        """
        Create TrustChain instance from YAML config file.

        Args:
            config_path: Path to YAML configuration file
            providers: List of LLM provider instances
            learned_parameters: LearnedParameters from feedback learning engine

        Returns:
            Configured TrustChain instance
        """
        config = TrustChainConfig.from_yaml(config_path)

        # Validate config
        errors = config.validate()
        if errors:
            for error in errors:
                if error.startswith("WARNING"):
                    logger.warning(error)
                else:
                    logger.error(error)

        return cls(config=config, providers=providers, learned_parameters=learned_parameters)

    @classmethod
    def from_dict(
        cls,
        config_dict: Dict[str, Any],
        providers: Optional[List[Any]] = None
    ) -> "TrustChain":
        """
        Create TrustChain instance from configuration dictionary.

        Args:
            config_dict: Configuration dictionary
            providers: List of LLM provider instances

        Returns:
            Configured TrustChain instance
        """
        config = TrustChainConfig.from_dict(config_dict)
        return cls(config=config, providers=providers)

    def _load_strategies(self, config: TrustChainConfig) -> List[BaseStrategy]:
        """Load strategies from configuration."""
        strategies = []
        for sc in config.get_enabled_strategies():
            try:
                strategy = self.registry.get_strategy(sc.name, sc.config)
                strategies.append(strategy)
                logger.debug(f"Loaded strategy: {sc.name}")
            except ValueError as e:
                logger.error(f"Failed to load strategy '{sc.name}': {e}")
        return strategies

    def _load_analyzers(self, config: TrustChainConfig) -> List[BaseAnalyzer]:
        """Load analyzers from configuration."""
        analyzers = []
        for ac in config.get_enabled_analyzers():
            try:
                analyzer = self.registry.get_analyzer(ac.name, ac.config)
                # Store blocking flag on instance
                analyzer._blocking = ac.blocking
                analyzers.append(analyzer)
                logger.debug(f"Loaded analyzer: {ac.name} (blocking={ac.blocking})")
            except ValueError as e:
                logger.error(f"Failed to load analyzer '{ac.name}': {e}")
        return analyzers

    def _load_outputs(self, config: TrustChainConfig) -> List[BaseOutput]:
        """Load output generators from configuration."""
        outputs = []
        for oc in config.get_enabled_outputs():
            try:
                output = self.registry.get_output(oc.name, oc.config)
                outputs.append(output)
                logger.debug(f"Loaded output: {oc.name}")
            except ValueError as e:
                logger.error(f"Failed to load output '{oc.name}': {e}")
        return outputs

    def _apply_learned_parameters(self, params: Any) -> None:
        """
        Apply learned parameters to strategies and analyzers.

        This is Phase 3 functionality - adjusts component behavior based
        on patterns learned from human feedback.

        Args:
            params: LearnedParameters object from learning engine
        """
        if not params:
            return

        logger.info("Applying learned parameters from feedback...")

        # Apply model weights to strategies that support it
        if params.model_weights:
            weight_dict = {mw.model_id: mw.weight for mw in params.model_weights}

            for strategy in self.strategies:
                if hasattr(strategy, 'set_model_weights'):
                    strategy.set_model_weights(weight_dict)
                    logger.debug(f"Applied model weights to strategy: {strategy.name}")
                elif strategy.name == "multi_model_consensus":
                    # Direct config update for multi-model consensus
                    if hasattr(strategy, 'config') and strategy.config:
                        if 'provider_weights' in strategy.config:
                            for model_id, weight in weight_dict.items():
                                # Match model_id to provider (e.g., "anthropic/claude-3" -> "anthropic")
                                provider = model_id.split("/")[0] if "/" in model_id else model_id
                                if provider in strategy.config['provider_weights']:
                                    old_weight = strategy.config['provider_weights'][provider]
                                    strategy.config['provider_weights'][provider] = weight
                                    logger.debug(
                                        f"Adjusted {provider} weight: {old_weight:.2f} -> {weight:.2f}"
                                    )

        # Apply analyzer tuning
        if params.analyzer_tuning:
            tuning_dict = {at.analyzer_name: at for at in params.analyzer_tuning}

            for analyzer in self.analyzers:
                if analyzer.name in tuning_dict:
                    tuning = tuning_dict[analyzer.name]

                    # Apply sensitivity multiplier if analyzer supports it
                    if hasattr(analyzer, 'adjust_sensitivity'):
                        analyzer.adjust_sensitivity(tuning.sensitivity_multiplier)
                        logger.debug(
                            f"Adjusted {analyzer.name} sensitivity: x{tuning.sensitivity_multiplier:.2f}"
                        )
                    elif hasattr(analyzer, 'config') and analyzer.config:
                        # Direct config adjustment for sensitivity
                        if 'sensitivity' in analyzer.config:
                            # Convert multiplier to sensitivity level
                            if tuning.sensitivity_multiplier > 1.2:
                                analyzer.config['sensitivity'] = 'high'
                            elif tuning.sensitivity_multiplier < 0.8:
                                analyzer.config['sensitivity'] = 'low'
                            else:
                                analyzer.config['sensitivity'] = 'medium'
                            logger.debug(
                                f"Set {analyzer.name} sensitivity to {analyzer.config['sensitivity']}"
                            )

        # Store confidence calibration for use during evaluation
        if params.confidence_calibration:
            self._confidence_calibration = {
                cc.reported_confidence: cc.actual_accuracy
                for cc in params.confidence_calibration
            }
            logger.debug(f"Loaded confidence calibration with {len(self._confidence_calibration)} points")
        else:
            self._confidence_calibration = {}

        logger.info(
            f"Applied learned parameters: "
            f"{len(params.model_weights)} model weights, "
            f"{len(params.analyzer_tuning)} analyzer tunings, "
            f"{len(params.confidence_calibration)} calibration points"
        )

    def _calibrate_confidence(self, reported_confidence: float) -> float:
        """
        Calibrate reported confidence based on learned accuracy.

        Uses linear interpolation between known calibration points.

        Args:
            reported_confidence: The raw confidence from the model

        Returns:
            Calibrated confidence reflecting actual accuracy
        """
        if not hasattr(self, '_confidence_calibration') or not self._confidence_calibration:
            return reported_confidence

        # Find nearest calibration points
        points = sorted(self._confidence_calibration.items())

        if not points:
            return reported_confidence

        # Exact match
        if reported_confidence in self._confidence_calibration:
            return self._confidence_calibration[reported_confidence]

        # Find surrounding points for interpolation
        lower = None
        upper = None

        for conf, acc in points:
            if conf <= reported_confidence:
                lower = (conf, acc)
            elif conf > reported_confidence and upper is None:
                upper = (conf, acc)

        # Edge cases
        if lower is None:
            return points[0][1]  # Below all points, use lowest
        if upper is None:
            return points[-1][1]  # Above all points, use highest

        # Linear interpolation
        lower_conf, lower_acc = lower
        upper_conf, upper_acc = upper

        ratio = (reported_confidence - lower_conf) / (upper_conf - lower_conf)
        return lower_acc + ratio * (upper_acc - lower_acc)

    async def evaluate(
        self,
        case_id: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        skip_analyzers: bool = False  # Phase 5: Skip analyzers for counterfactual re-runs
    ) -> AccountabilityResult:
        """
        Run full TrustChain evaluation.

        This is the main entry point for evaluating a case. It:
        1. Runs all configured evaluation strategies
        2. Runs all configured analyzers on the results (unless skip_analyzers=True)
        3. Determines the final decision based on thresholds
        4. Generates all configured outputs
        5. Returns a complete AccountabilityResult

        Args:
            case_id: Unique identifier for this case
            input_data: The case/application data to evaluate
            context: Policy context, criteria, etc.
            dry_run: If True, validate config and return expected execution
                     without calling LLM providers (saves API costs)
            skip_analyzers: If True, skip running analyzers (used for counterfactual
                           re-runs to avoid infinite recursion)

        Returns:
            Complete AccountabilityResult with decision, analysis, and audit trail
        """
        context = context or {}
        result_id = f"tc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Handle dry run mode
        if dry_run:
            return await self._dry_run_evaluate(result_id, case_id, input_data, context)

        logger.info(f"Starting TrustChain evaluation: {result_id} for case {case_id}"
                    + (" (skip_analyzers=True)" if skip_analyzers else ""))

        # Initialize result
        result = AccountabilityResult(
            result_id=result_id,
            case_id=case_id,
            decision_type=self.config.decision_type if self.config else context.get("decision_type", "general"),
            final_decision=DecisionOutcome.NEEDS_REVIEW,
            overall_confidence=0.0,
            requires_human_review=False,
            config_snapshot=self.config.to_dict() if self.config else {}
        )

        # Calculate input data hash for integrity
        result.input_data_hash = self._calculate_hash(input_data)

        # STEP 1: Run evaluation strategies
        logger.info(f"Running {len(self.strategies)} evaluation strategies...")
        strategy_results = await self._run_strategies(input_data, context)

        # Combine strategy results
        result.strategy_result = self._combine_strategy_results(strategy_results)

        if result.strategy_result:
            result.primary_reasoning = result.strategy_result.reasoning
            result.overall_confidence = result.strategy_result.confidence

        # STEP 2: Run analyzers (unless skipped for counterfactual re-runs)
        if not skip_analyzers:
            logger.info(f"Running {len(self.analyzers)} analyzers...")
            result = await self._run_analyzers(result, input_data, context)
        else:
            logger.info("Skipping analyzers (counterfactual re-run mode)")

        # STEP 3: Determine final decision
        result = self._determine_final_decision(result)

        # STEP 4: Generate outputs
        logger.info(f"Generating {len(self.outputs)} outputs...")
        generated_outputs = await self._generate_outputs(result)

        # Extract consumer summary if available
        if "consumer_explanation" in generated_outputs:
            consumer_output = generated_outputs["consumer_explanation"]
            if isinstance(consumer_output, dict):
                result.consumer_summary = consumer_output.get("summary")
                result.feedback_points = consumer_output.get("feedback", [])

        # Finalize with audit hash
        result = result.finalize(input_data)

        logger.info(
            f"Evaluation complete: {result.final_decision.value} "
            f"(confidence={result.overall_confidence:.0%}, "
            f"review={result.requires_human_review})"
        )

        return result

    async def _run_strategies(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[StrategyResult]:
        """Run all evaluation strategies."""
        results = []

        for strategy in self.strategies:
            try:
                # Check if strategy can execute with available providers
                if not strategy.can_execute(self.providers):
                    logger.warning(
                        f"Strategy '{strategy.name}' cannot execute: "
                        f"requires {strategy.min_providers} providers, "
                        f"have {len(self.providers)}"
                    )
                    continue

                logger.info(f"  Running strategy: {strategy.name}")
                sr = await strategy.evaluate(input_data, context, self.providers)
                results.append(sr)
                logger.info(
                    f"    Result: {sr.decision.value} "
                    f"(confidence={sr.confidence:.0%})"
                )

            except Exception as e:
                logger.error(f"  Strategy '{strategy.name}' failed: {e}")
                # Add error to review triggers if configured
                if self.config and self.config.human_review_on_error:
                    # Will be handled in _determine_final_decision
                    pass

        return results

    async def _run_analyzers(
        self,
        result: AccountabilityResult,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AccountabilityResult:
        """Run all analyzers on the strategy result."""
        if not result.strategy_result:
            logger.warning("No strategy result to analyze")
            return result

        for analyzer in self.analyzers:
            try:
                logger.info(f"  Running analyzer: {analyzer.name}")

                # Use async version if available
                if hasattr(analyzer, 'analyze_async'):
                    # Phase 5: Pass trustchain_instance to counterfactual analyzer
                    if analyzer.name == "counterfactual_fairness":
                        ar = await analyzer.analyze_async(
                            result.strategy_result, input_data, context,
                            trustchain_instance=self
                        )
                    else:
                        ar = await analyzer.analyze_async(
                            result.strategy_result, input_data, context
                        )
                else:
                    ar = analyzer.analyze(
                        result.strategy_result, input_data, context
                    )

                result.analysis_results.append(ar)

                status = "PASSED" if ar.passed else "FLAGGED"
                logger.info(f"    Result: {status}")

                # Check if blocking analyzer failed
                is_blocking = getattr(analyzer, '_blocking', analyzer.blocking)
                if not ar.passed and is_blocking:
                    result.requires_human_review = True

                    if ar.detected_attributes:
                        result.review_triggers.append(ReviewTrigger.BIAS_DETECTED)
                        result.concerns.extend(
                            [f"Protected attribute: {attr}" for attr in ar.detected_attributes]
                        )

                    if ar.detected_proxies:
                        result.review_triggers.append(ReviewTrigger.PROXY_DETECTED)

                    if ar.flags:
                        result.concerns.extend(ar.flags)

            except Exception as e:
                logger.error(f"  Analyzer '{analyzer.name}' failed: {e}")
                result.review_triggers.append(ReviewTrigger.ANALYZER_FAILED)
                if self.config and self.config.human_review_on_error:
                    result.requires_human_review = True

        return result

    async def _generate_outputs(
        self,
        result: AccountabilityResult
    ) -> Dict[str, Any]:
        """Generate all configured outputs."""
        generated = {}

        for output in self.outputs:
            try:
                logger.debug(f"  Generating output: {output.name}")

                # Use async version if available
                if hasattr(output, 'generate_async'):
                    generated[output.name] = await output.generate_async(result)
                else:
                    generated[output.name] = output.generate(result)

            except Exception as e:
                logger.error(f"  Output '{output.name}' failed: {e}")
                generated[output.name] = {"error": str(e)}

        return generated

    def _combine_strategy_results(
        self,
        results: List[StrategyResult]
    ) -> Optional[StrategyResult]:
        """Combine multiple strategy results into one."""
        if not results:
            return None

        if len(results) == 1:
            return results[0]

        # Multiple strategies - need to reconcile
        from collections import Counter

        decisions = [r.decision for r in results]
        confidences = [r.confidence for r in results]

        # Majority decision
        decision_counts = Counter(decisions)
        majority_decision = decision_counts.most_common(1)[0][0]

        # Average confidence
        avg_confidence = sum(confidences) / len(confidences)

        # Agreement level
        agreement = decision_counts[majority_decision] / len(decisions)

        # Collect dissenting views
        dissenting_views = [
            r.reasoning for r in results if r.decision != majority_decision
        ]

        return StrategyResult(
            strategy_name="combined",
            decision=majority_decision,
            confidence=avg_confidence,
            reasoning=(
                f"Combined result from {len(results)} strategies "
                f"with {agreement:.0%} agreement"
            ),
            agreement_level=agreement,
            dissenting_views=dissenting_views,
            model_decisions=[],  # Individual model decisions are in each strategy result
        )

    def _determine_final_decision(
        self,
        result: AccountabilityResult
    ) -> AccountabilityResult:
        """Determine final decision based on strategy results and analysis."""
        sr = result.strategy_result

        if not sr:
            result.final_decision = DecisionOutcome.NEEDS_REVIEW
            result.requires_human_review = True
            result.review_triggers.append(ReviewTrigger.STRATEGY_ERROR)
            return result

        result.overall_confidence = sr.confidence

        # Get thresholds from config or use defaults
        min_conf = self.config.min_confidence if self.config else 0.7

        # Check confidence threshold
        if sr.confidence < min_conf:
            result.requires_human_review = True
            result.review_triggers.append(ReviewTrigger.LOW_CONFIDENCE)

        # Check agreement level (for multi-model strategies)
        if sr.agreement_level is not None and sr.agreement_level < 0.66:
            result.requires_human_review = True
            result.review_triggers.append(ReviewTrigger.CONSENSUS_DISAGREEMENT)

        # Set final decision
        if result.review_triggers:
            result.requires_human_review = True
            result.final_decision = DecisionOutcome.NEEDS_REVIEW
        else:
            result.final_decision = sr.decision

        return result

    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash of data for integrity verification."""
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()

    def add_provider(self, provider: Any) -> None:
        """Add an LLM provider to the service."""
        self.providers.append(provider)
        logger.info(f"Added provider: {provider.__class__.__name__}")

    def add_strategy(self, strategy: BaseStrategy) -> None:
        """Add an evaluation strategy to the service."""
        self.strategies.append(strategy)
        logger.info(f"Added strategy: {strategy.name}")

    def add_analyzer(self, analyzer: BaseAnalyzer, blocking: bool = True) -> None:
        """Add an analyzer to the service."""
        analyzer._blocking = blocking
        self.analyzers.append(analyzer)
        logger.info(f"Added analyzer: {analyzer.name} (blocking={blocking})")

    def add_output(self, output: BaseOutput) -> None:
        """Add an output generator to the service."""
        self.outputs.append(output)
        logger.info(f"Added output: {output.name}")

    def get_component_summary(self) -> Dict[str, Any]:
        """Get summary of loaded components."""
        return {
            "strategies": [s.name for s in self.strategies],
            "analyzers": [a.name for a in self.analyzers],
            "outputs": [o.name for o in self.outputs],
            "providers": [p.__class__.__name__ for p in self.providers],
            "config_loaded": self.config is not None,
        }

    async def _dry_run_evaluate(
        self,
        result_id: str,
        case_id: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AccountabilityResult:
        """
        Perform a dry run evaluation without calling LLM providers.

        This validates the configuration and shows what would be executed,
        useful for testing pipeline setup before spending API credits.

        Returns:
            AccountabilityResult with dry_run metadata instead of real decisions
        """
        logger.info(f"DRY RUN: Validating evaluation pipeline for case {case_id}")

        # Build execution plan
        execution_plan = {
            "mode": "dry_run",
            "case_id": case_id,
            "result_id": result_id,
            "decision_type": self.config.decision_type if self.config else context.get("decision_type", "general"),
            "input_data_fields": list(input_data.keys()),
            "input_data_hash": self._calculate_hash(input_data),
        }

        # Validate strategies
        strategy_validation = []
        for strategy in self.strategies:
            can_execute = strategy.can_execute(self.providers)
            strategy_info = {
                "name": strategy.name,
                "version": strategy.version,
                "description": strategy.description,
                "requires_multiple_providers": strategy.requires_multiple_providers,
                "min_providers": strategy.min_providers,
                "can_execute": can_execute,
                "config": strategy.config,
            }

            if not can_execute:
                strategy_info["warning"] = (
                    f"Cannot execute: requires {strategy.min_providers} providers, "
                    f"have {len(self.providers)}"
                )

            strategy_validation.append(strategy_info)

        execution_plan["strategies"] = strategy_validation

        # Validate analyzers
        analyzer_validation = []
        for analyzer in self.analyzers:
            is_blocking = getattr(analyzer, '_blocking', analyzer.blocking)
            analyzer_validation.append({
                "name": analyzer.name,
                "version": analyzer.version,
                "description": analyzer.description,
                "blocking": is_blocking,
                "config": analyzer.config,
            })

        execution_plan["analyzers"] = analyzer_validation

        # Validate outputs
        output_validation = []
        for output in self.outputs:
            output_validation.append({
                "name": output.name,
                "version": output.version,
                "description": output.description,
                "output_format": output.output_format,
                "config": output.config,
            })

        execution_plan["outputs"] = output_validation

        # Validate providers
        provider_validation = []
        for provider in self.providers:
            provider_info = {
                "class": provider.__class__.__name__,
                "available": True,  # Assume available if instantiated
            }

            # Get provider details if available
            if hasattr(provider, 'model_name'):
                provider_info["model"] = provider.model_name
            if hasattr(provider, 'provider_name'):
                provider_info["provider"] = provider.provider_name

            provider_validation.append(provider_info)

        execution_plan["providers"] = provider_validation

        # Check for issues
        issues = []
        warnings = []

        if not self.strategies:
            issues.append("No strategies configured")

        if not self.providers:
            issues.append("No LLM providers configured")

        executable_strategies = [s for s in strategy_validation if s.get("can_execute")]
        if self.strategies and not executable_strategies:
            issues.append("No strategies can execute with current provider count")

        if not self.analyzers:
            warnings.append("No analyzers configured - bias checks will not run")

        if not self.outputs:
            warnings.append("No output generators configured")

        # Config thresholds
        if self.config:
            execution_plan["thresholds"] = {
                "min_confidence": self.config.min_confidence,
                "auto_approve_threshold": self.config.auto_approve_threshold,
                "auto_deny_threshold": self.config.auto_deny_threshold,
            }
            execution_plan["settings"] = {
                "fail_open": self.config.fail_open,
                "require_all_strategies": self.config.require_all_strategies,
                "human_review_on_error": self.config.human_review_on_error,
            }

        execution_plan["issues"] = issues
        execution_plan["warnings"] = warnings
        execution_plan["ready_to_execute"] = len(issues) == 0

        # Build result
        result = AccountabilityResult(
            result_id=result_id,
            case_id=case_id,
            decision_type=execution_plan["decision_type"],
            final_decision=DecisionOutcome.NEEDS_REVIEW,
            overall_confidence=0.0,
            requires_human_review=True,
            config_snapshot=self.config.to_dict() if self.config else {},
            primary_reasoning="DRY RUN - No actual evaluation performed",
        )

        result.input_data_hash = execution_plan["input_data_hash"]

        # Store execution plan in metadata
        result.strategy_result = StrategyResult(
            strategy_name="dry_run",
            decision=DecisionOutcome.NEEDS_REVIEW,
            confidence=0.0,
            reasoning="DRY RUN - Pipeline validation only",
            metadata={
                "execution_plan": execution_plan,
                "ready": execution_plan["ready_to_execute"],
            }
        )

        # Add dry run analysis result
        from core.result import AnalysisResult

        result.analysis_results.append(AnalysisResult(
            analyzer_name="dry_run_validator",
            passed=len(issues) == 0,
            flags=issues,
            warnings=warnings,
            recommendation=(
                "Pipeline is ready for execution"
                if len(issues) == 0
                else f"Fix {len(issues)} issue(s) before execution"
            ),
            metadata={"execution_plan": execution_plan}
        ))

        # Finalize (without input_data to avoid confusion)
        result.audit_hash = result.calculate_audit_hash()

        logger.info(
            f"DRY RUN complete: ready={execution_plan['ready_to_execute']}, "
            f"issues={len(issues)}, warnings={len(warnings)}"
        )

        return result

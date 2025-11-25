# TrustChain Phase 3: Feedback & Learning System

**Purpose**: Transform TrustChain from reactive bias detection into an adaptive learning system that improves over time based on human decisions.

**Author**: Kareem Primo + Claude (November 2025)

---

## Why This Matters

Phases 1-2 built detection. Phase 3 builds intelligence.

Right now TrustChain can say "this decision looks suspicious." After Phase 3, it can say:
- "Decisions like this get overturned 73% of the time"
- "Model X is overconfident on immigration cases"
- "This reviewer's overrides correlate with worse outcomes"

This is what makes TrustChain a **training guardrail** for new AI systems, not just an auditor.

---

## Core Concept: The Feedback Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRUSTCHAIN DECISION                          │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                        │
│              │   NEEDS_REVIEW flagged │                        │
│              └────────────────────────┘                        │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                        │
│              │   Human Reviews Case   │                        │
│              └────────────────────────┘                        │
│                           │                                     │
│              ┌────────────┴────────────┐                       │
│              ▼                         ▼                        │
│     ┌──────────────┐          ┌──────────────┐                 │
│     │   AGREES     │          │  OVERRIDES   │                 │
│     │ with TC flag │          │ TC decision  │                 │
│     └──────────────┘          └──────────────┘                 │
│              │                         │                        │
│              └────────────┬────────────┘                       │
│                           ▼                                     │
│              ┌────────────────────────┐                        │
│              │   Feedback Captured    │                        │
│              │   - reviewer_id        │                        │
│              │   - action taken       │                        │
│              │   - reasoning          │                        │
│              │   - timestamp          │                        │
│              └────────────────────────┘                        │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                        │
│              │   Learning Engine      │                        │
│              │   Updates:             │                        │
│              │   - Model weights      │                        │
│              │   - Confidence curves  │                        │
│              │   - Flag accuracy      │                        │
│              └────────────────────────┘                        │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                        │
│              │  Future decisions      │                        │
│              │  are smarter           │                        │
│              └────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## What We're Building

### 3.1 Feedback Capture System

**New file**: `backend/feedback/capture.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class ReviewerAction(str, Enum):
    """What the human reviewer decided."""
    AGREE_APPROVE = "agree_approve"      # TC said approve, human agrees
    AGREE_DENY = "agree_deny"            # TC said deny, human agrees
    AGREE_FLAG = "agree_flag"            # TC flagged, human agrees it needed review
    OVERRIDE_TO_APPROVE = "override_approve"  # TC said deny/flag, human approves
    OVERRIDE_TO_DENY = "override_deny"        # TC said approve/flag, human denies
    ESCALATE = "escalate"                # Human escalates to higher authority
    REQUEST_MORE_INFO = "request_info"   # Can't decide, need more data


class OverrideReason(str, Enum):
    """Why the human overrode TrustChain."""
    CONTEXT_NOT_CAPTURED = "context_not_captured"  # TC missed relevant context
    FALSE_POSITIVE_BIAS = "false_positive_bias"    # Flag was wrong
    FALSE_NEGATIVE_BIAS = "false_negative_bias"    # Should have flagged, didn't
    POLICY_EXCEPTION = "policy_exception"          # Special case allowed by policy
    MODEL_HALLUCINATION = "model_hallucination"    # AI made stuff up
    CRITERIA_MISAPPLIED = "criteria_misapplied"    # AI got the rules wrong
    OTHER = "other"


@dataclass
class HumanFeedback:
    """Captured feedback from human reviewer."""
    
    # Link to original decision
    result_id: str
    case_id: str
    
    # Reviewer info
    reviewer_id: str
    reviewer_role: str  # "sr_reviewer", "manager", "legal", etc.
    
    # What they decided
    action: ReviewerAction
    override_reason: Optional[OverrideReason] = None
    
    # Their reasoning (critical for learning)
    reasoning: str = ""
    
    # What they saw that TC missed (or flagged incorrectly)
    additional_context: str = ""
    
    # Did any specific analyzer get it wrong?
    incorrect_flags: List[str] = field(default_factory=list)  # ["proxy_variables"]
    missed_flags: List[str] = field(default_factory=list)     # ["protected_attributes"]
    
    # Confidence in their decision
    reviewer_confidence: float = 1.0  # 0.0-1.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    time_spent_seconds: Optional[int] = None  # How long they reviewed
    
    # For outcome tracking (filled in later)
    outcome_tracked: bool = False
    final_outcome: Optional[str] = None  # What actually happened
    outcome_timestamp: Optional[datetime] = None


@dataclass
class FeedbackStats:
    """Aggregated statistics from feedback."""
    
    total_decisions: int = 0
    total_reviewed: int = 0
    
    # Agreement rates
    agreement_rate: float = 0.0  # How often humans agree with TC
    override_rate: float = 0.0   # How often humans override TC
    
    # By analyzer
    analyzer_accuracy: Dict[str, float] = field(default_factory=dict)
    # e.g., {"proxy_variables": 0.89, "protected_attributes": 0.95}
    
    # By model (for multi-model consensus)
    model_accuracy: Dict[str, float] = field(default_factory=dict)
    # e.g., {"anthropic": 0.91, "openai": 0.87, "llama": 0.82}
    
    # False positive/negative rates
    false_positive_rate: float = 0.0  # Flagged but shouldn't have
    false_negative_rate: float = 0.0  # Didn't flag but should have
    
    # By decision type
    accuracy_by_type: Dict[str, float] = field(default_factory=dict)
    # e.g., {"hiring": 0.88, "lending": 0.92}
```

### 3.2 Feedback Storage

**New file**: `backend/feedback/storage.py`

```python
"""
Feedback storage interface.

Supports multiple backends:
- SQLite (local dev)
- PostgreSQL (production)
- In-memory (testing)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .capture import HumanFeedback, FeedbackStats


class FeedbackStore(ABC):
    """Abstract base for feedback storage."""
    
    @abstractmethod
    async def save_feedback(self, feedback: HumanFeedback) -> str:
        """Save feedback, return ID."""
        pass
    
    @abstractmethod
    async def get_feedback(self, result_id: str) -> Optional[HumanFeedback]:
        """Get feedback for a specific decision."""
        pass
    
    @abstractmethod
    async def get_feedback_batch(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        limit: int = 1000
    ) -> List[HumanFeedback]:
        """Query feedback with filters."""
        pass
    
    @abstractmethod
    async def compute_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> FeedbackStats:
        """Compute aggregate statistics."""
        pass
    
    @abstractmethod
    async def update_outcome(
        self,
        result_id: str,
        final_outcome: str,
        outcome_timestamp: datetime
    ) -> bool:
        """Update with final outcome (for tracking long-term accuracy)."""
        pass


class SQLiteFeedbackStore(FeedbackStore):
    """SQLite implementation for local dev."""
    
    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        # Implementation: create feedback table with all fields
        pass
    
    # ... implement abstract methods ...


class InMemoryFeedbackStore(FeedbackStore):
    """In-memory store for testing."""
    
    def __init__(self):
        self._feedback: Dict[str, HumanFeedback] = {}
    
    async def save_feedback(self, feedback: HumanFeedback) -> str:
        self._feedback[feedback.result_id] = feedback
        return feedback.result_id
    
    # ... implement other methods ...
```

### 3.3 Learning Engine

**New file**: `backend/learning/engine.py`

This is the brain. It takes feedback and updates TrustChain's behavior.

```python
"""
Learning Engine for TrustChain.

Takes human feedback and improves future decisions by:
1. Adjusting model weights in multi-model consensus
2. Calibrating confidence scores
3. Tuning analyzer sensitivity
4. Identifying patterns in overrides
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from feedback.storage import FeedbackStore
from feedback.capture import HumanFeedback, ReviewerAction


@dataclass
class ModelWeight:
    """Learned weight for a model."""
    model_name: str
    base_weight: float = 1.0
    learned_adjustment: float = 0.0  # Can be negative
    
    # Breakdown by decision type
    type_adjustments: Dict[str, float] = field(default_factory=dict)
    
    # Track history
    last_updated: datetime = field(default_factory=datetime.now)
    feedback_count: int = 0
    
    @property
    def effective_weight(self) -> float:
        return max(0.1, self.base_weight + self.learned_adjustment)
    
    def weight_for_type(self, decision_type: str) -> float:
        adjustment = self.type_adjustments.get(decision_type, 0.0)
        return max(0.1, self.base_weight + self.learned_adjustment + adjustment)


@dataclass
class ConfidenceCalibration:
    """Learned confidence calibration."""
    
    # Calibration curve: reported confidence -> actual accuracy
    # e.g., when model says 90%, it's actually right 75% of the time
    calibration_curve: Dict[str, float] = field(default_factory=dict)
    # Keys are buckets: "0.5-0.6", "0.6-0.7", etc.
    
    # Per-model calibration
    model_calibration: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def calibrate(self, raw_confidence: float, model: Optional[str] = None) -> float:
        """Return calibrated confidence."""
        bucket = f"{int(raw_confidence * 10) / 10:.1f}-{int(raw_confidence * 10) / 10 + 0.1:.1f}"
        
        if model and model in self.model_calibration:
            curve = self.model_calibration[model]
        else:
            curve = self.calibration_curve
        
        if bucket in curve:
            return curve[bucket]
        return raw_confidence  # No calibration data yet


@dataclass 
class AnalyzerTuning:
    """Learned sensitivity tuning for analyzers."""
    
    analyzer_name: str
    
    # If false positive rate is high, reduce sensitivity
    # If false negative rate is high, increase sensitivity
    sensitivity_adjustment: float = 0.0  # -1.0 to 1.0
    
    # Patterns that were false positives (should ignore)
    false_positive_patterns: List[str] = field(default_factory=list)
    
    # Patterns that were false negatives (should add)
    missed_patterns: List[str] = field(default_factory=list)
    
    # Per-decision-type adjustments
    type_sensitivity: Dict[str, float] = field(default_factory=dict)


class LearningEngine:
    """
    Main learning engine.
    
    Usage:
        engine = LearningEngine(feedback_store)
        
        # Learn from accumulated feedback
        await engine.learn()
        
        # Get learned parameters for a decision
        params = engine.get_parameters("hiring")
        
        # Apply to TrustChain config
        tc = TrustChain(
            model_weights=params.model_weights,
            confidence_calibration=params.calibration,
            analyzer_tuning=params.analyzer_tuning
        )
    """
    
    def __init__(
        self,
        feedback_store: FeedbackStore,
        learning_rate: float = 0.1,
        min_feedback_count: int = 10  # Need this many before adjusting
    ):
        self.store = feedback_store
        self.learning_rate = learning_rate
        self.min_feedback = min_feedback_count
        
        # Learned parameters
        self.model_weights: Dict[str, ModelWeight] = {}
        self.calibration = ConfidenceCalibration()
        self.analyzer_tuning: Dict[str, AnalyzerTuning] = {}
        
        # Learning metadata
        self.last_trained: Optional[datetime] = None
        self.training_feedback_count: int = 0
    
    async def learn(
        self,
        since: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Learn from feedback and update parameters.
        
        Returns summary of what was learned.
        """
        # Get feedback
        feedback_list = await self.store.get_feedback_batch(
            start_date=since or (datetime.now() - timedelta(days=30)),
            decision_type=decision_type
        )
        
        if len(feedback_list) < self.min_feedback:
            return {"status": "insufficient_data", "count": len(feedback_list)}
        
        # Learn model weights
        model_updates = self._learn_model_weights(feedback_list)
        
        # Learn confidence calibration
        calibration_updates = self._learn_calibration(feedback_list)
        
        # Learn analyzer tuning
        analyzer_updates = self._learn_analyzer_tuning(feedback_list)
        
        # Update metadata
        self.last_trained = datetime.now()
        self.training_feedback_count = len(feedback_list)
        
        return {
            "status": "success",
            "feedback_count": len(feedback_list),
            "model_updates": model_updates,
            "calibration_updates": calibration_updates,
            "analyzer_updates": analyzer_updates
        }
    
    def _learn_model_weights(self, feedback: List[HumanFeedback]) -> Dict[str, Any]:
        """Update model weights based on which models were right."""
        # Count correct/incorrect per model
        model_correct: Dict[str, int] = {}
        model_total: Dict[str, int] = {}
        
        for fb in feedback:
            # Need to look up original decision to see which models voted how
            # This would come from the stored AccountabilityResult
            # For each model in the decision:
            #   - If human agreed, model was "correct"
            #   - If human overrode, model was "incorrect"
            pass
        
        # Update weights
        updates = {}
        for model, total in model_total.items():
            if total >= self.min_feedback:
                accuracy = model_correct.get(model, 0) / total
                
                # Adjust weight toward accuracy
                if model not in self.model_weights:
                    self.model_weights[model] = ModelWeight(model_name=model)
                
                current = self.model_weights[model].learned_adjustment
                target = accuracy - 0.5  # Center around 0.5 accuracy
                new_adjustment = current + self.learning_rate * (target - current)
                
                self.model_weights[model].learned_adjustment = new_adjustment
                self.model_weights[model].feedback_count = total
                self.model_weights[model].last_updated = datetime.now()
                
                updates[model] = {
                    "accuracy": accuracy,
                    "new_weight": self.model_weights[model].effective_weight
                }
        
        return updates
    
    def _learn_calibration(self, feedback: List[HumanFeedback]) -> Dict[str, Any]:
        """Learn confidence calibration from feedback."""
        # Group by confidence bucket
        buckets: Dict[str, List[bool]] = {}  # bucket -> list of correct/incorrect
        
        for fb in feedback:
            # Need original confidence from AccountabilityResult
            # correct = (fb.action in [AGREE_APPROVE, AGREE_DENY, AGREE_FLAG])
            pass
        
        # Update calibration curve
        updates = {}
        for bucket, outcomes in buckets.items():
            if len(outcomes) >= self.min_feedback:
                actual_accuracy = sum(outcomes) / len(outcomes)
                self.calibration.calibration_curve[bucket] = actual_accuracy
                updates[bucket] = actual_accuracy
        
        return updates
    
    def _learn_analyzer_tuning(self, feedback: List[HumanFeedback]) -> Dict[str, Any]:
        """Learn analyzer sensitivity from false positives/negatives."""
        # Count false positives per analyzer
        false_positives: Dict[str, int] = {}
        false_negatives: Dict[str, int] = {}
        totals: Dict[str, int] = {}
        
        for fb in feedback:
            for analyzer in fb.incorrect_flags:
                false_positives[analyzer] = false_positives.get(analyzer, 0) + 1
                totals[analyzer] = totals.get(analyzer, 0) + 1
            
            for analyzer in fb.missed_flags:
                false_negatives[analyzer] = false_negatives.get(analyzer, 0) + 1
                totals[analyzer] = totals.get(analyzer, 0) + 1
        
        # Adjust sensitivity
        updates = {}
        for analyzer, total in totals.items():
            if total >= self.min_feedback:
                fp_rate = false_positives.get(analyzer, 0) / total
                fn_rate = false_negatives.get(analyzer, 0) / total
                
                if analyzer not in self.analyzer_tuning:
                    self.analyzer_tuning[analyzer] = AnalyzerTuning(analyzer_name=analyzer)
                
                # High FP rate -> reduce sensitivity
                # High FN rate -> increase sensitivity
                adjustment = (fn_rate - fp_rate) * self.learning_rate
                self.analyzer_tuning[analyzer].sensitivity_adjustment += adjustment
                
                updates[analyzer] = {
                    "fp_rate": fp_rate,
                    "fn_rate": fn_rate,
                    "new_sensitivity": self.analyzer_tuning[analyzer].sensitivity_adjustment
                }
        
        return updates
    
    def get_parameters(self, decision_type: Optional[str] = None) -> "LearnedParameters":
        """Get current learned parameters."""
        return LearnedParameters(
            model_weights={k: v.weight_for_type(decision_type) if decision_type else v.effective_weight 
                          for k, v in self.model_weights.items()},
            calibration=self.calibration,
            analyzer_sensitivity={k: v.sensitivity_adjustment 
                                 for k, v in self.analyzer_tuning.items()},
            last_trained=self.last_trained,
            feedback_count=self.training_feedback_count
        )
    
    def export_state(self) -> Dict[str, Any]:
        """Export learned state for persistence."""
        return {
            "model_weights": {k: v.__dict__ for k, v in self.model_weights.items()},
            "calibration": self.calibration.__dict__,
            "analyzer_tuning": {k: v.__dict__ for k, v in self.analyzer_tuning.items()},
            "last_trained": self.last_trained.isoformat() if self.last_trained else None,
            "feedback_count": self.training_feedback_count
        }
    
    def import_state(self, state: Dict[str, Any]):
        """Import previously learned state."""
        # Reconstruct from dict
        pass


@dataclass
class LearnedParameters:
    """Parameters learned from feedback, ready to apply."""
    model_weights: Dict[str, float]
    calibration: ConfidenceCalibration
    analyzer_sensitivity: Dict[str, float]
    last_trained: Optional[datetime]
    feedback_count: int
```

### 3.4 Feedback API Endpoints

**Update**: `backend/app.py`

```python
from fastapi import APIRouter, HTTPException
from feedback.capture import HumanFeedback, ReviewerAction, OverrideReason
from feedback.storage import get_feedback_store
from learning.engine import LearningEngine

feedback_router = APIRouter(prefix="/api/v2/feedback", tags=["feedback"])


@feedback_router.post("/submit")
async def submit_feedback(
    result_id: str,
    reviewer_id: str,
    action: ReviewerAction,
    reasoning: str = "",
    override_reason: Optional[OverrideReason] = None,
    incorrect_flags: List[str] = [],
    missed_flags: List[str] = []
):
    """
    Submit human feedback on a TrustChain decision.
    
    Called after a human reviews a flagged case.
    """
    feedback = HumanFeedback(
        result_id=result_id,
        case_id="",  # Lookup from result_id
        reviewer_id=reviewer_id,
        reviewer_role="",  # Lookup from reviewer_id
        action=action,
        override_reason=override_reason,
        reasoning=reasoning,
        incorrect_flags=incorrect_flags,
        missed_flags=missed_flags
    )
    
    store = get_feedback_store()
    feedback_id = await store.save_feedback(feedback)
    
    return {"status": "captured", "feedback_id": feedback_id}


@feedback_router.get("/stats")
async def get_feedback_stats(
    decision_type: Optional[str] = None,
    days: int = 30
):
    """Get aggregate feedback statistics."""
    store = get_feedback_store()
    since = datetime.now() - timedelta(days=days)
    
    stats = await store.compute_stats(start_date=since, decision_type=decision_type)
    return stats


@feedback_router.post("/learn")
async def trigger_learning(
    decision_type: Optional[str] = None,
    days: int = 30
):
    """
    Trigger learning from accumulated feedback.
    
    Updates model weights, confidence calibration, and analyzer tuning.
    """
    store = get_feedback_store()
    engine = LearningEngine(store)
    
    since = datetime.now() - timedelta(days=days)
    results = await engine.learn(since=since, decision_type=decision_type)
    
    # Persist learned state
    # engine.export_state() -> save to file or DB
    
    return results


@feedback_router.get("/parameters")
async def get_learned_parameters(decision_type: Optional[str] = None):
    """Get current learned parameters for TrustChain config."""
    store = get_feedback_store()
    engine = LearningEngine(store)
    
    # Load previously learned state
    # engine.import_state(...)
    
    params = engine.get_parameters(decision_type)
    return params


@feedback_router.post("/outcome")
async def record_outcome(
    result_id: str,
    final_outcome: str,
    notes: str = ""
):
    """
    Record the final outcome of a decision.
    
    For long-term accuracy tracking. Called weeks/months later
    when you know if the decision was actually good.
    
    Example:
    - Hired candidate -> did they succeed or fail?
    - Approved loan -> did they default or repay?
    """
    store = get_feedback_store()
    success = await store.update_outcome(
        result_id=result_id,
        final_outcome=final_outcome,
        outcome_timestamp=datetime.now()
    )
    
    return {"status": "recorded" if success else "not_found"}
```

### 3.5 Integration with TrustChain Service

**Update**: `backend/services/trustchain.py`

Add learned parameters support:

```python
class TrustChain:
    def __init__(
        self,
        config: Optional[TrustChainConfig] = None,
        # ... existing params ...
        learned_parameters: Optional[LearnedParameters] = None  # NEW
    ):
        self.learned = learned_parameters
        
        # Apply learned model weights to consensus strategy
        if self.learned and self.learned.model_weights:
            for strategy in self.strategies:
                if hasattr(strategy, 'set_model_weights'):
                    strategy.set_model_weights(self.learned.model_weights)
        
        # Apply analyzer sensitivity adjustments
        if self.learned and self.learned.analyzer_sensitivity:
            for analyzer in self.analyzers:
                if analyzer.name in self.learned.analyzer_sensitivity:
                    adjustment = self.learned.analyzer_sensitivity[analyzer.name]
                    if hasattr(analyzer, 'adjust_sensitivity'):
                        analyzer.adjust_sensitivity(adjustment)
    
    async def evaluate(self, ...):
        # ... existing code ...
        
        # Apply confidence calibration before final decision
        if self.learned and sr:
            sr.confidence = self.learned.calibration.calibrate(
                sr.confidence,
                model=sr.strategy_name
            )
        
        # ... rest of evaluation ...
```

---

## New Directory Structure

```
backend/
├── feedback/           # NEW
│   ├── __init__.py
│   ├── capture.py      # HumanFeedback, ReviewerAction, etc.
│   └── storage.py      # FeedbackStore implementations
│
├── learning/           # NEW
│   ├── __init__.py
│   └── engine.py       # LearningEngine, ModelWeight, etc.
│
├── ... existing ...
```

---

## Phase 3 TODO Checklist

```
[ ] Create backend/feedback/ directory
[ ] Implement feedback/capture.py with HumanFeedback dataclass
[ ] Implement feedback/storage.py with abstract FeedbackStore
[ ] Implement SQLiteFeedbackStore for local dev
[ ] Implement InMemoryFeedbackStore for testing
[ ] Create backend/learning/ directory
[ ] Implement learning/engine.py with LearningEngine
[ ] Implement ModelWeight, ConfidenceCalibration, AnalyzerTuning
[ ] Implement LearnedParameters export/import
[ ] Add feedback API endpoints to app.py
[ ] Update TrustChain service to accept LearnedParameters
[ ] Update multi_model_consensus strategy with set_model_weights()
[ ] Update analyzers with adjust_sensitivity() method
[ ] Write tests for feedback capture
[ ] Write tests for learning engine
[ ] Write tests for API endpoints
[ ] Add example of full feedback loop in docs
```

---

## Example: Complete Feedback Loop

```python
# 1. TrustChain makes decision
tc = TrustChain.from_config("configs/hiring.yaml")
result = await tc.evaluate(case_id="candidate_123", input_data={...})
# result.requires_human_review = True (flagged culture fit)

# 2. Human reviews and provides feedback
feedback = HumanFeedback(
    result_id=result.result_id,
    case_id="candidate_123",
    reviewer_id="hr_manager_jane",
    reviewer_role="hiring_manager",
    action=ReviewerAction.OVERRIDE_TO_APPROVE,
    override_reason=OverrideReason.FALSE_POSITIVE_BIAS,
    reasoning="The 'culture fit' mention was about team collaboration style, not discriminatory",
    incorrect_flags=["proxy_variables"],
    additional_context="Candidate's portfolio showed strong teamwork examples"
)
await feedback_store.save_feedback(feedback)

# 3. After accumulating feedback, train
engine = LearningEngine(feedback_store)
results = await engine.learn()
# {
#   "model_updates": {"anthropic": {"accuracy": 0.89, "new_weight": 1.02}},
#   "analyzer_updates": {"proxy_variables": {"fp_rate": 0.15, "new_sensitivity": -0.02}}
# }

# 4. Future decisions use learned parameters
params = engine.get_parameters("hiring")
tc = TrustChain.from_config("configs/hiring.yaml", learned_parameters=params)
# Now proxy_variables is slightly less sensitive, reducing false positives
```

---

## Key Design Decisions

1. **Feedback is explicit, not implicit** - We don't try to infer from whether someone clicked "proceed." Reviewers explicitly say what they did and why.

2. **Learning is batched, not real-time** - We don't update weights after every single feedback. We accumulate and learn periodically (daily/weekly).

3. **Minimum feedback threshold** - Won't adjust anything until we have enough data (default: 10 samples).

4. **Learning rate is conservative** - Small adjustments (0.1 default) to avoid overcorrecting.

5. **Everything is auditable** - Feedback, learning runs, parameter changes all logged.

6. **Outcome tracking is separate** - Immediate feedback (did human agree?) vs long-term outcome (did the decision work out?).

---

## Questions for Implementation

1. Should learning be triggered automatically (cron) or manually (API call)?
2. Should we support "unlearning" if feedback is later discovered to be bad?
3. How do we handle conflicting feedback from different reviewers?
4. Should learned parameters be versioned for rollback?

---

*Document generated November 2025. TrustChain - Learning from every decision.*

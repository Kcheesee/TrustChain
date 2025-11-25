"""
TrustChain FastAPI Application

REST API for multi-model AI decision-making with government compliance.

Endpoints:
    v1 (Legacy - Orchestrator-based):
    - POST /api/v1/decisions - Submit new decision request
    - GET /api/v1/decisions/{decision_id} - Retrieve decision
    - GET /api/v1/health - System health check
    - GET /api/v1/providers/status - AI provider status

    v2 (New - Modular TrustChain service):
    - POST /api/v2/evaluate - Evaluate using TrustChain service
    - GET /api/v2/components - List registered components
    - GET /api/v2/config/{config_name} - Load and validate config

    v2 Feedback (Phase 3 - Learning System):
    - POST /api/v2/feedback/submit - Submit human feedback on decisions
    - GET /api/v2/feedback/stats - Get aggregate feedback statistics
    - POST /api/v2/feedback/learn - Trigger learning cycle
    - GET /api/v2/feedback/parameters - Get learned parameters
    - POST /api/v2/feedback/outcome - Record long-term outcome
    - GET /api/v2/feedback/{result_id} - Get feedback for specific result

    v2 Safeguards (Bad Actor Protection):
    - GET /api/v2/safeguards/report - Comprehensive safeguards report
    - GET /api/v2/safeguards/reviewer/{id} - Reviewer credibility details
    - POST /api/v2/safeguards/rollback/{version} - Roll back parameters
    - POST /api/v2/safeguards/flag-reviewer/{id} - Flag bad actor
    - POST /api/v2/safeguards/unflag-reviewer/{id} - Unflag reviewer

Run with: uvicorn app:app --reload

Built with care by Kareem & Claude
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pydantic import BaseModel

from providers import ProviderConfig
from services import DecisionOrchestrator, TrustChain
from models import DecisionRequest, DecisionResponse, DecisionStatus

# Import core components to register them
from core.registry import get_registry

# Phase 3: Feedback and Learning System
from feedback import (
    HumanFeedback,
    ReviewerAction,
    OverrideReason,
    FeedbackStats,
    get_feedback_store,
    set_feedback_store,
    FeedbackStore,
    PostgresFeedbackStore,
)
from learning import LearningEngine, LearnedParameters, LearningGuard

# Phase 4: Database Integration
from database import init_database, get_db_manager
import strategies  # noqa: F401 - Registers strategy components
import analyzers  # noqa: F401 - Registers analyzer components
import outputs  # noqa: F401 - Registers output components

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
orchestrator: Optional[DecisionOrchestrator] = None
trustchain_service: Optional[TrustChain] = None
feedback_store: Optional[FeedbackStore] = None
learning_engine: Optional[LearningEngine] = None
learning_guard: Optional[LearningGuard] = None  # Bad actor protection

# In-memory storage (will be replaced with database)
decision_store: Dict[str, Any] = {}  # Legacy v1 decisions
accountability_store: Dict[str, Any] = {}  # New v2 results


# Request models for v2 API
class EvaluateRequest(BaseModel):
    """Request model for TrustChain evaluation."""
    case_id: str
    decision_type: str
    input_data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    config_name: Optional[str] = None  # Load from configs/ directory


class ConfigLoadRequest(BaseModel):
    """Request model for loading a configuration."""
    config_name: str


# Request models for Feedback API (Phase 3)
class FeedbackSubmitRequest(BaseModel):
    """Request model for submitting human feedback."""
    result_id: str
    case_id: str
    reviewer_id: str
    action: str  # ReviewerAction value
    reasoning: Optional[str] = None
    override_reason: Optional[str] = None  # OverrideReason value
    incorrect_flags: Optional[List[str]] = None
    missed_flags: Optional[List[str]] = None
    notes: Optional[str] = None


class OutcomeRecordRequest(BaseModel):
    """Request model for recording long-term outcome."""
    result_id: str
    outcome: str  # e.g., "successful_hire", "appeal_overturned", "complaint_filed"
    outcome_details: Optional[Dict[str, Any]] = None


class LearnRequest(BaseModel):
    """Request model for triggering learning."""
    decision_type: Optional[str] = None
    force: bool = False  # Skip minimum feedback count check


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Initializes both legacy orchestrator and new TrustChain service on startup.
    This runs once when the server starts, not on every request.
    """
    global orchestrator, trustchain_service, feedback_store, learning_engine, learning_guard

    logger.info("🚀 Starting TrustChain API...")

    # Phase 4: Initialize PostgreSQL database if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            db_manager = init_database(database_url, echo=os.getenv("DB_ECHO", "false").lower() == "true")
            db_manager.init_db()  # Create tables
            logger.info("✓ PostgreSQL database connected and initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.warning("Falling back to SQLite for feedback storage")
            database_url = None

    # Initialize AI provider configurations
    anthropic_config = None
    openai_config = None
    llama_config = None
    providers = []

    if os.getenv("ANTHROPIC_API_KEY"):
        anthropic_config = ProviderConfig(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_retries=3,
            timeout_seconds=60
        )
        logger.info("✓ Anthropic provider configured")

    if os.getenv("OPENAI_API_KEY"):
        openai_config = ProviderConfig(
            api_key=os.getenv("OPENAI_API_KEY"),
            max_retries=3,
            timeout_seconds=60
        )
        logger.info("✓ OpenAI provider configured")

    if os.getenv("OLLAMA_BASE_URL"):
        llama_config = ProviderConfig(
            max_retries=2,
            timeout_seconds=90
        )
        logger.info("✓ Llama provider configured")

    # Create legacy orchestrator (v1 API)
    orchestrator = DecisionOrchestrator(
        anthropic_config=anthropic_config,
        openai_config=openai_config,
        llama_config=llama_config,
        require_consensus_threshold=float(os.getenv("CONSENSUS_THRESHOLD", "0.66"))
    )

    # Initialize TrustChain service (v2 API) with providers from orchestrator
    trustchain_service = TrustChain(providers=orchestrator.providers)

    # Phase 3: Initialize feedback store, safeguards, and learning engine
    # Use PostgreSQL if DATABASE_URL is configured, otherwise default to SQLite
    if database_url:
        try:
            db_manager = get_db_manager()
            feedback_store = PostgresFeedbackStore(db_manager.get_session_direct)
            set_feedback_store(feedback_store)
            logger.info("✓ Using PostgreSQL for feedback storage")
        except Exception as e:
            logger.warning(f"Failed to create PostgresFeedbackStore: {e}")
            feedback_store = get_feedback_store()  # Fallback to SQLite
    else:
        feedback_store = get_feedback_store()  # Default SQLite

    # Initialize bad actor protection (LearningGuard)
    learning_guard = LearningGuard(
        max_reviewer_influence=float(os.getenv("MAX_REVIEWER_INFLUENCE", "0.15")),
        outcome_wait_days=int(os.getenv("OUTCOME_WAIT_DAYS", "90")),
        min_outcome_sample=int(os.getenv("MIN_OUTCOME_SAMPLE", "20")),
        anomaly_override_threshold=float(os.getenv("ANOMALY_OVERRIDE_THRESHOLD", "0.4")),
        min_credibility_for_learning=float(os.getenv("MIN_CREDIBILITY", "0.3")),
        state_path=os.getenv("SAFEGUARD_STATE_PATH", "data/safeguards_state.json"),
    )
    logger.info("✓ LearningGuard initialized (bad actor protection)")

    learning_engine = LearningEngine(
        feedback_store=feedback_store,
        learning_rate=float(os.getenv("LEARNING_RATE", "0.1")),
        min_feedback_count=int(os.getenv("MIN_FEEDBACK_COUNT", "10")),
        state_path=os.getenv("LEARNING_STATE_PATH", "data/learned_state.json"),
        safeguard=learning_guard,  # Connect safeguards
    )
    logger.info("✓ Feedback store and learning engine initialized (with safeguards)")

    # Log registered components
    registry = get_registry()
    components = registry.list_components()
    logger.info(
        f"Registered components: "
        f"{len(components['strategies'])} strategies, "
        f"{len(components['analyzers'])} analyzers, "
        f"{len(components['outputs'])} outputs"
    )

    logger.info("✅ TrustChain API ready (v1 + v2 endpoints available)")

    yield  # Server runs here

    # Cleanup on shutdown
    logger.info("Shutting down TrustChain API...")


# Create FastAPI application
app = FastAPI(
    title="TrustChain API",
    description="Multi-model AI decision-making with bias detection and audit trails",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (allows frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "service": "TrustChain API",
        "version": "1.0.0",
        "description": "Multi-model AI decision-making with government compliance",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get("/api/v1/health")
async def health_check():
    """
    Health check endpoint.

    Returns system status and provider health metrics.
    Use this for monitoring and load balancer health checks.
    """
    if not orchestrator:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "message": "Orchestrator not initialized"}
        )

    health_status = orchestrator.get_provider_health()

    # Determine overall status
    overall_status = "healthy"
    if health_status["healthy_providers"] == 0:
        overall_status = "critical"
    elif health_status["overall_health"] < 0.5:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "providers": health_status,
        "decisions_processed": len(decision_store)
    }


@app.get("/api/v1/providers/status")
async def provider_status():
    """
    Get detailed status of all AI providers.

    Returns individual provider metrics including:
    - Health status (healthy/degraded/unavailable)
    - Total requests made
    - Error count and rate
    - Health score (0-1)
    """
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized"
        )

    health_info = orchestrator.get_provider_health()

    return {
        "total_providers": health_info["total_providers"],
        "healthy_providers": health_info["healthy_providers"],
        "overall_health": health_info["overall_health"],
        "providers": health_info["providers"],
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/decisions", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
async def create_decision(request: DecisionRequest):
    """
    Submit a new decision request.

    This is the MAIN endpoint - submits a case to all AI models,
    gets consensus, runs bias detection, and returns the decision.

    Args:
        request: DecisionRequest with case details

    Returns:
        DecisionResponse with consensus decision and audit trail

    Example:
        POST /api/v1/decisions
        {
            "case_id": "unemp_001",
            "decision_type": "unemployment_benefits",
            "input_data": {"employment_months": 18, ...},
            "policy_context": "State unemployment eligibility...",
            "require_consensus": true
        }
    """
    if not orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready - orchestrator not initialized"
        )

    logger.info(f"📥 New decision request: {request.case_id}")

    try:
        # Create the prompt from input data
        prompt = _format_prompt(request)

        # Make the decision using orchestrator
        decision = await orchestrator.make_decision(
            case_id=request.case_id,
            decision_type=request.decision_type,
            prompt=prompt,
            policy_context=request.policy_context,
            input_data=request.input_data
        )

        # Store decision (in-memory for now, will use database later)
        decision_store[decision.decision_id] = decision

        logger.info(
            f"✅ Decision complete: {decision.decision_id} - "
            f"{decision.final_decision.value} ({decision.status.value})"
        )

        # Build response
        response = DecisionResponse(
            decision_id=decision.decision_id,
            status=decision.status,
            final_decision=decision.final_decision,
            consensus_analysis=decision.consensus_analysis,
            model_decisions=decision.model_decisions,
            requires_human_review=(decision.status == DecisionStatus.REQUIRES_REVIEW),
            audit_hash=decision.audit_hash
        )

        return response

    except Exception as e:
        logger.error(f"❌ Decision request failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decision processing failed: {str(e)}"
        )


@app.get("/api/v1/decisions/{decision_id}")
async def get_decision(decision_id: str):
    """
    Retrieve a decision by ID.

    Returns the full decision record including:
    - Final decision and status
    - Consensus analysis
    - Individual model decisions with reasoning
    - Bias detection results
    - Audit hash for verification

    Args:
        decision_id: Unique decision identifier

    Returns:
        Complete Decision object
    """
    if decision_id not in decision_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found"
        )

    decision = decision_store[decision_id]

    # Verify audit hash
    hash_valid = decision.verify_audit_hash()

    return {
        "decision": decision.dict(),
        "audit_verified": hash_valid,
        "foia_report": decision.to_foia_report()
    }


@app.get("/api/v1/decisions")
async def list_decisions(
    status_filter: Optional[str] = None,
    decision_type: Optional[str] = None,
    limit: int = 100
):
    """
    List recent decisions with optional filtering.

    Query Parameters:
        status: Filter by status (pending/completed/requires_review)
        decision_type: Filter by type (unemployment_benefits/etc)
        limit: Max results to return (default 100)

    Returns:
        List of decision summaries
    """
    decisions = list(decision_store.values())

    # Apply filters
    if status_filter:
        decisions = [d for d in decisions if d.status.value == status_filter]

    if decision_type:
        decisions = [d for d in decisions if d.decision_type == decision_type]

    # Limit results
    decisions = decisions[:limit]

    # Return summaries (not full details)
    return {
        "total": len(decision_store),
        "filtered": len(decisions),
        "decisions": [
            {
                "decision_id": d.decision_id,
                "case_id": d.case_id,
                "decision_type": d.decision_type,
                "final_decision": d.final_decision.value if d.final_decision else None,
                "status": d.status.value,
                "created_at": d.created_at.isoformat(),
                "requires_review": d.status == DecisionStatus.REQUIRES_REVIEW,
                "consensus_level": d.consensus_analysis.agreement_level if d.consensus_analysis else None
            }
            for d in decisions
        ]
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_prompt(request: DecisionRequest) -> str:
    """
    Format input data into a prompt for AI models.

    This creates a human-readable case description from structured data.
    """
    # Extract key fields based on decision type
    if request.decision_type == "unemployment_benefits":
        return f"""
Unemployment Benefits Application - Case #{request.case_id}

Applicant Details:
- Employment Duration: {request.input_data.get('employment_duration_months', 'N/A')} months
- Reason for Separation: {request.input_data.get('termination_reason', 'N/A')}
- Prior Annual Earnings: ${request.input_data.get('prior_earnings_annual', 'N/A')}
- Available for Work: {request.input_data.get('available_for_work', 'N/A')}
- Actively Seeking Work: {request.input_data.get('actively_seeking_work', 'N/A')}
- Has Refused Suitable Work: {request.input_data.get('refused_suitable_work', False)}

Please evaluate this application and provide:
1. Your decision (APPROVE or DENY)
2. Step-by-step reasoning based on eligibility criteria
3. Your confidence level in this decision
"""

    # Generic format for other decision types
    else:
        formatted_data = "\n".join([f"- {k}: {v}" for k, v in request.input_data.items()])
        return f"""
Decision Request - Case #{request.case_id}
Type: {request.decision_type}

Case Details:
{formatted_data}

Please evaluate this case and provide:
1. Your decision
2. Step-by-step reasoning
3. Your confidence level
"""


# ============================================================================
# V2 API ENDPOINTS - Modular TrustChain Service
# ============================================================================

@app.post("/api/v2/evaluate", status_code=status.HTTP_201_CREATED)
async def evaluate_v2(request: EvaluateRequest):
    """
    Evaluate a case using the new modular TrustChain service.

    This endpoint uses the plugin-based architecture with configurable
    strategies, analyzers, and outputs.

    Args:
        request: EvaluateRequest with case details and optional config

    Returns:
        AccountabilityResult with decision, analysis, and audit trail

    Example:
        POST /api/v2/evaluate
        {
            "case_id": "unemp_001",
            "decision_type": "unemployment_benefits",
            "input_data": {"employment_months": 18, ...},
            "config_name": "unemployment_benefits"
        }
    """
    global trustchain_service

    if not trustchain_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TrustChain service not initialized"
        )

    logger.info(f"📥 [v2] New evaluation request: {request.case_id}")

    try:
        # Load config if specified
        if request.config_name:
            config_path = Path(__file__).parent.parent / "configs" / f"{request.config_name}.yaml"
            if config_path.exists():
                trustchain_service = TrustChain.from_config(
                    str(config_path),
                    providers=orchestrator.providers if orchestrator else []
                )
                logger.info(f"Loaded config: {request.config_name}")
            else:
                logger.warning(f"Config not found: {config_path}, using defaults")

        # Build context
        context = request.context or {}
        context["decision_type"] = request.decision_type

        # Build prompt if not provided
        if "prompt" not in context:
            context["prompt"] = _format_prompt_v2(request)
            context["system_context"] = context.get("policy_context", "")

        # Run evaluation
        result = await trustchain_service.evaluate(
            case_id=request.case_id,
            input_data=request.input_data,
            context=context
        )

        # Store result
        accountability_store[result.result_id] = result

        logger.info(
            f"✅ [v2] Evaluation complete: {result.result_id} - "
            f"{result.final_decision.value} (review={result.requires_human_review})"
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"❌ [v2] Evaluation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )


@app.get("/api/v2/results/{result_id}")
async def get_result_v2(result_id: str):
    """
    Retrieve an accountability result by ID.

    Returns the full AccountabilityResult including:
    - Final decision and confidence
    - Strategy execution details
    - Analysis results from all analyzers
    - Audit hash for verification
    """
    if result_id not in accountability_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result {result_id} not found"
        )

    result = accountability_store[result_id]

    return {
        "result": result.to_dict(),
        "audit_verified": result.verify_integrity(),
        "foia_report": result.to_foia_report()
    }


@app.get("/api/v2/results")
async def list_results_v2(
    decision_type: Optional[str] = None,
    requires_review: Optional[bool] = None,
    limit: int = Query(default=100, le=1000)
):
    """
    List accountability results with optional filtering.

    Query Parameters:
        decision_type: Filter by type (unemployment_benefits/hiring/etc)
        requires_review: Filter by review status
        limit: Max results to return (default 100, max 1000)
    """
    results = list(accountability_store.values())

    # Apply filters
    if decision_type:
        results = [r for r in results if r.decision_type == decision_type]

    if requires_review is not None:
        results = [r for r in results if r.requires_human_review == requires_review]

    # Limit and return summaries
    results = results[:limit]

    return {
        "total": len(accountability_store),
        "filtered": len(results),
        "results": [
            {
                "result_id": r.result_id,
                "case_id": r.case_id,
                "decision_type": r.decision_type,
                "final_decision": r.final_decision.value,
                "confidence": r.overall_confidence,
                "requires_review": r.requires_human_review,
                "review_triggers": [t.value for t in r.review_triggers],
                "timestamp": r.timestamp.isoformat(),
            }
            for r in results
        ]
    }


@app.get("/api/v2/components")
async def list_components():
    """
    List all registered TrustChain components.

    Returns available strategies, analyzers, and output generators
    that can be used in configurations.
    """
    registry = get_registry()
    return {
        "components": registry.list_components(),
        "metadata": registry.get_component_metadata(),
    }


@app.get("/api/v2/configs")
async def list_configs():
    """
    List available configuration files.

    Returns list of YAML configs in the configs/ directory.
    """
    config_dir = Path(__file__).parent.parent / "configs"
    if not config_dir.exists():
        return {"configs": []}

    configs = []
    for config_file in config_dir.glob("*.yaml"):
        configs.append({
            "name": config_file.stem,
            "path": str(config_file),
        })

    return {"configs": configs}


@app.get("/api/v2/configs/{config_name}")
async def get_config(config_name: str):
    """
    Load and validate a configuration file.

    Args:
        config_name: Name of config (without .yaml extension)

    Returns:
        Parsed configuration with validation results
    """
    from core.config import TrustChainConfig

    config_path = Path(__file__).parent.parent / "configs" / f"{config_name}.yaml"

    if not config_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config '{config_name}' not found"
        )

    try:
        config = TrustChainConfig.from_yaml(str(config_path))
        errors = config.validate()

        return {
            "name": config_name,
            "config": config.to_dict(),
            "valid": len([e for e in errors if not e.startswith("WARNING")]) == 0,
            "warnings": [e for e in errors if e.startswith("WARNING")],
            "errors": [e for e in errors if not e.startswith("WARNING")],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to load config: {str(e)}"
        )


def _format_prompt_v2(request: EvaluateRequest) -> str:
    """Format input data into a prompt for v2 API."""
    formatted_data = "\n".join([f"- {k}: {v}" for k, v in request.input_data.items()])
    return f"""
Decision Request - Case #{request.case_id}
Type: {request.decision_type}

Case Details:
{formatted_data}

Please evaluate this case and provide:
1. Your decision (APPROVE, DENY, or NEEDS_REVIEW)
2. Step-by-step reasoning
3. Your confidence level (0-1)
"""


# ============================================================================
# V2 FEEDBACK API ENDPOINTS (Phase 3)
# ============================================================================

@app.post("/api/v2/feedback/submit", status_code=status.HTTP_201_CREATED)
async def submit_feedback(request: FeedbackSubmitRequest):
    """
    Submit human feedback on a TrustChain decision.

    This endpoint captures reviewer feedback when they agree with,
    override, or escalate an AI-generated decision.

    Args:
        request: FeedbackSubmitRequest with reviewer action and reasoning

    Returns:
        Confirmation with feedback ID

    Example:
        POST /api/v2/feedback/submit
        {
            "result_id": "tc_abc123",
            "case_id": "hire_456",
            "reviewer_id": "jane_hr",
            "action": "override_deny",
            "reasoning": "Candidate has relevant experience not captured",
            "override_reason": "context_not_captured"
        }
    """
    if not feedback_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback store not initialized"
        )

    logger.info(f"📝 Feedback submission: {request.result_id} by {request.reviewer_id}")

    try:
        # Validate action
        try:
            action = ReviewerAction(request.action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action. Valid values: {[a.value for a in ReviewerAction]}"
            )

        # Validate override_reason if provided
        override_reason = None
        if request.override_reason:
            try:
                override_reason = OverrideReason(request.override_reason)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid override_reason. Valid values: {[r.value for r in OverrideReason]}"
                )

        # Get original result for context
        original_decision = None
        original_confidence = None
        model_decisions = None
        if request.result_id in accountability_store:
            result = accountability_store[request.result_id]
            original_decision = result.final_decision.value
            original_confidence = result.overall_confidence
            # Extract model decisions if available
            if hasattr(result, 'strategy_results'):
                for sr in result.strategy_results:
                    if hasattr(sr, 'model_responses'):
                        model_decisions = {
                            r.model_id: r.decision.value
                            for r in sr.model_responses
                            if hasattr(r, 'model_id') and hasattr(r, 'decision')
                        }

        # Create feedback object
        feedback = HumanFeedback(
            result_id=request.result_id,
            case_id=request.case_id,
            reviewer_id=request.reviewer_id,
            action=action,
            reasoning=request.reasoning,
            override_reason=override_reason,
            incorrect_flags=request.incorrect_flags,
            missed_flags=request.missed_flags,
            notes=request.notes,
            original_decision=original_decision,
            original_confidence=original_confidence,
            model_decisions=model_decisions,
        )

        # Save to store
        await feedback_store.save_feedback(feedback)

        logger.info(f"✅ Feedback saved: {feedback.feedback_id}")

        return {
            "feedback_id": feedback.feedback_id,
            "result_id": request.result_id,
            "action": action.value,
            "is_override": action.is_override,
            "timestamp": feedback.timestamp.isoformat(),
            "message": "Feedback recorded successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Feedback submission failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save feedback: {str(e)}"
        )


@app.get("/api/v2/feedback/stats")
async def get_feedback_stats(
    decision_type: Optional[str] = None,
    reviewer_id: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365)
):
    """
    Get aggregate feedback statistics.

    Returns metrics on reviewer agreement, override rates, and patterns.

    Query Parameters:
        decision_type: Filter by decision type (hiring/unemployment_benefits/etc)
        reviewer_id: Filter by specific reviewer
        days: Number of days to include (default 30, max 365)

    Returns:
        FeedbackStats with aggregate metrics
    """
    if not feedback_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback store not initialized"
        )

    try:
        stats = await feedback_store.compute_stats(
            decision_type=decision_type,
            reviewer_id=reviewer_id,
            days=days
        )

        return {
            "stats": {
                "total_feedback": stats.total_feedback,
                "agreement_rate": stats.agreement_rate,
                "override_rate": stats.override_rate,
                "escalation_rate": stats.escalation_rate,
                "override_reasons": stats.override_reasons,
                "by_decision_type": stats.by_decision_type,
                "by_reviewer": stats.by_reviewer,
                "false_positive_rate": stats.false_positive_rate,
                "false_negative_rate": stats.false_negative_rate,
            },
            "filters": {
                "decision_type": decision_type,
                "reviewer_id": reviewer_id,
                "days": days,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to compute stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute statistics: {str(e)}"
        )


@app.post("/api/v2/feedback/learn")
async def trigger_learning(request: LearnRequest):
    """
    Trigger a learning cycle to update model weights and calibration.

    This analyzes accumulated feedback and adjusts:
    - Model weights based on individual accuracy
    - Confidence calibration curves
    - Analyzer sensitivity thresholds

    Args:
        request: LearnRequest with optional decision_type and force flag

    Returns:
        Learning results with before/after comparisons

    Example:
        POST /api/v2/feedback/learn
        {
            "decision_type": "hiring",
            "force": false
        }
    """
    if not learning_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning engine not initialized"
        )

    logger.info(f"🧠 Learning cycle triggered (type={request.decision_type}, force={request.force})")

    try:
        results = await learning_engine.learn(
            decision_type=request.decision_type,
            force=request.force
        )

        logger.info(f"✅ Learning complete: {results.get('feedback_processed', 0)} feedback processed")

        return {
            "success": True,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Learning failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Learning cycle failed: {str(e)}"
        )


@app.get("/api/v2/feedback/parameters")
async def get_learned_parameters(decision_type: Optional[str] = None):
    """
    Get current learned parameters.

    Returns the parameters learned from feedback that can be applied
    to TrustChain for improved accuracy.

    Query Parameters:
        decision_type: Filter parameters for specific decision type

    Returns:
        LearnedParameters with model weights, calibration, and tuning
    """
    if not learning_engine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning engine not initialized"
        )

    try:
        params = learning_engine.get_parameters(decision_type=decision_type)

        return {
            "parameters": {
                "model_weights": [
                    {
                        "model_id": mw.model_id,
                        "weight": mw.weight,
                        "accuracy": mw.accuracy,
                        "feedback_count": mw.feedback_count,
                    }
                    for mw in params.model_weights
                ],
                "confidence_calibration": [
                    {
                        "reported_confidence": cc.reported_confidence,
                        "actual_accuracy": cc.actual_accuracy,
                        "sample_count": cc.sample_count,
                    }
                    for cc in params.confidence_calibration
                ],
                "analyzer_tuning": [
                    {
                        "analyzer_name": at.analyzer_name,
                        "sensitivity_multiplier": at.sensitivity_multiplier,
                        "false_positive_rate": at.false_positive_rate,
                        "false_negative_rate": at.false_negative_rate,
                    }
                    for at in params.analyzer_tuning
                ],
                "last_updated": params.last_updated.isoformat() if params.last_updated else None,
                "feedback_count": params.feedback_count,
            },
            "decision_type": decision_type,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to get parameters: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get parameters: {str(e)}"
        )


@app.post("/api/v2/feedback/outcome")
async def record_outcome(request: OutcomeRecordRequest):
    """
    Record the long-term outcome of a decision.

    This captures what actually happened after the decision was made,
    enabling learning from real-world results.

    Args:
        request: OutcomeRecordRequest with outcome details

    Returns:
        Confirmation of outcome recording

    Example:
        POST /api/v2/feedback/outcome
        {
            "result_id": "tc_abc123",
            "outcome": "successful_hire",
            "outcome_details": {"performance_rating": 4.5, "retention_months": 12}
        }
    """
    if not feedback_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback store not initialized"
        )

    logger.info(f"📊 Outcome recording: {request.result_id} -> {request.outcome}")

    try:
        # Update feedback with outcome
        await feedback_store.update_outcome(
            result_id=request.result_id,
            outcome=request.outcome,
            outcome_details=request.outcome_details
        )

        logger.info(f"✅ Outcome recorded: {request.result_id}")

        return {
            "result_id": request.result_id,
            "outcome": request.outcome,
            "timestamp": datetime.now().isoformat(),
            "message": "Outcome recorded successfully",
        }

    except Exception as e:
        logger.error(f"❌ Outcome recording failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record outcome: {str(e)}"
        )


@app.get("/api/v2/feedback/{result_id}")
async def get_feedback_for_result(result_id: str):
    """
    Get all feedback for a specific result.

    Returns all feedback entries linked to a TrustChain result,
    including any outcome data recorded later.

    Args:
        result_id: The TrustChain result ID

    Returns:
        List of feedback entries for this result
    """
    if not feedback_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback store not initialized"
        )

    try:
        feedback_list = await feedback_store.get_feedback(result_id=result_id)

        return {
            "result_id": result_id,
            "feedback_count": len(feedback_list),
            "feedback": [
                {
                    "feedback_id": f.feedback_id,
                    "reviewer_id": f.reviewer_id,
                    "action": f.action.value,
                    "reasoning": f.reasoning,
                    "override_reason": f.override_reason.value if f.override_reason else None,
                    "timestamp": f.timestamp.isoformat(),
                    "outcome": f.outcome,
                    "outcome_recorded_at": f.outcome_recorded_at.isoformat() if f.outcome_recorded_at else None,
                }
                for f in feedback_list
            ],
        }

    except Exception as e:
        logger.error(f"❌ Failed to get feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feedback: {str(e)}"
        )


# ============================================================================
# V2 SAFEGUARDS API ENDPOINTS (Bad Actor Protection)
# ============================================================================

@app.get("/api/v2/safeguards/report")
async def get_safeguards_report():
    """
    Get comprehensive safeguards report.

    Returns current state of bad actor protections including:
    - Flagged reviewers and their anomalies
    - Reviewer credibility scores
    - Parameter version history
    - Overall system health

    Returns:
        SafeguardsReport with all protection metrics
    """
    if not learning_guard:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning safeguards not initialized"
        )

    try:
        report = learning_guard.get_safeguards_report()

        return {
            "safeguards": report,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to get safeguards report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get safeguards report: {str(e)}"
        )


@app.get("/api/v2/safeguards/reviewer/{reviewer_id}")
async def get_reviewer_credibility(reviewer_id: str):
    """
    Get credibility details for a specific reviewer.

    Returns outcome-based accuracy, override patterns, and any anomalies
    detected for this reviewer.

    Args:
        reviewer_id: The reviewer's ID

    Returns:
        ReviewerCredibility details
    """
    if not learning_guard:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning safeguards not initialized"
        )

    try:
        if reviewer_id not in learning_guard.reviewer_credibility:
            return {
                "reviewer_id": reviewer_id,
                "status": "unknown",
                "message": "No data for this reviewer yet",
            }

        cred = learning_guard.reviewer_credibility[reviewer_id]

        return {
            "reviewer": cred.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to get reviewer credibility: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviewer credibility: {str(e)}"
        )


@app.post("/api/v2/safeguards/rollback/{version}")
async def rollback_parameters(version: int):
    """
    Roll back learned parameters to a previous version.

    Use this if corruption is detected or parameters are performing poorly.

    Args:
        version: The version number to roll back to

    Returns:
        Confirmation and the restored parameters
    """
    if not learning_guard:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning safeguards not initialized"
        )

    try:
        restored = learning_guard.rollback_to_version(version)

        if restored is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found"
            )

        logger.warning(f"🔙 Parameters rolled back to version {version}")

        return {
            "status": "success",
            "rolled_back_to": version,
            "timestamp": datetime.now().isoformat(),
            "message": f"Parameters rolled back to version {version}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Rollback failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(e)}"
        )


@app.post("/api/v2/safeguards/flag-reviewer/{reviewer_id}")
async def flag_reviewer(reviewer_id: str, reason: str = Query(...)):
    """
    Manually flag a reviewer for exclusion from learning.

    Use this if you identify a bad actor through external means.

    Args:
        reviewer_id: The reviewer to flag
        reason: Why they're being flagged

    Returns:
        Confirmation of flagging
    """
    if not learning_guard:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning safeguards not initialized"
        )

    try:
        if reviewer_id not in learning_guard.reviewer_credibility:
            from learning import ReviewerCredibility
            learning_guard.reviewer_credibility[reviewer_id] = ReviewerCredibility(
                reviewer_id=reviewer_id
            )

        cred = learning_guard.reviewer_credibility[reviewer_id]
        cred.flagged_for_review = True
        cred.flag_reason = f"Manual flag: {reason}"

        logger.warning(f"🚩 Reviewer {reviewer_id} manually flagged: {reason}")

        return {
            "status": "flagged",
            "reviewer_id": reviewer_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to flag reviewer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to flag reviewer: {str(e)}"
        )


@app.post("/api/v2/safeguards/unflag-reviewer/{reviewer_id}")
async def unflag_reviewer(reviewer_id: str, reason: str = Query(...)):
    """
    Remove flag from a reviewer, allowing their feedback to be used again.

    Args:
        reviewer_id: The reviewer to unflag
        reason: Why they're being unflagged

    Returns:
        Confirmation of unflagging
    """
    if not learning_guard:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Learning safeguards not initialized"
        )

    try:
        if reviewer_id not in learning_guard.reviewer_credibility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reviewer {reviewer_id} not found"
            )

        cred = learning_guard.reviewer_credibility[reviewer_id]
        cred.flagged_for_review = False
        cred.flag_reason = ""

        logger.info(f"✅ Reviewer {reviewer_id} unflagged: {reason}")

        return {
            "status": "unflagged",
            "reviewer_id": reviewer_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to unflag reviewer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unflag reviewer: {str(e)}"
        )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch-all exception handler for unexpected errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info"
    )

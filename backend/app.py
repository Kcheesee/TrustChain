"""
TrustChain FastAPI Application

REST API for multi-model AI decision-making with government compliance.

Endpoints:
- POST /api/v1/decisions - Submit new decision request
- GET /api/v1/decisions/{decision_id} - Retrieve decision
- GET /api/v1/health - System health check
- GET /api/v1/providers/status - AI provider status

Run with: uvicorn app:app --reload
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from providers import ProviderConfig
from services import DecisionOrchestrator
from models import DecisionRequest, DecisionResponse, DecisionStatus

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: Optional[DecisionOrchestrator] = None

# In-memory decision storage (will be replaced with database)
# Format: {decision_id: Decision}
decision_store: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Initializes the orchestrator on startup, cleans up on shutdown.
    This runs once when the server starts, not on every request.
    """
    global orchestrator

    logger.info("🚀 Starting TrustChain API...")

    # Initialize AI provider configurations
    anthropic_config = None
    openai_config = None
    llama_config = None

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

    # Create orchestrator
    orchestrator = DecisionOrchestrator(
        anthropic_config=anthropic_config,
        openai_config=openai_config,
        llama_config=llama_config,
        require_consensus_threshold=float(os.getenv("CONSENSUS_THRESHOLD", "0.66"))
    )

    logger.info("✅ TrustChain API ready")

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

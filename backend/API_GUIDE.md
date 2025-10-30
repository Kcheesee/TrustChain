# TrustChain API Guide

Complete guide to using the TrustChain REST API for multi-model AI decisions.

---

## 🚀 Quick Start

### 1. Start the Server

```bash
cd backend
uvicorn app:app --reload
```

Server runs at: `http://localhost:8000`

### 2. View Interactive Docs

Open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. Run Tests

```bash
# In another terminal
python test_api.py
```

---

## 📡 API Endpoints

### Health Check

```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "providers": {
    "total_providers": 3,
    "healthy_providers": 3,
    "overall_health": 1.0
  },
  "decisions_processed": 42
}
```

**Use Cases:**
- Load balancer health checks
- Monitoring/alerting
- Pre-flight checks before submitting decisions

---

### Provider Status

```http
GET /api/v1/providers/status
```

**Response:**
```json
{
  "total_providers": 3,
  "healthy_providers": 3,
  "overall_health": 1.0,
  "providers": [
    {
      "provider": "anthropic",
      "status": "healthy",
      "total_requests": 150,
      "total_errors": 2,
      "error_rate": 0.013,
      "health_score": 0.987
    },
    // ... more providers
  ]
}
```

**Use Cases:**
- Dashboard displays
- Debugging provider issues
- Capacity planning

---

### Submit Decision (Main Endpoint)

```http
POST /api/v1/decisions
Content-Type: application/json
```

**Request Body:**
```json
{
  "case_id": "unemp_001",
  "decision_type": "unemployment_benefits",
  "input_data": {
    "employment_duration_months": 18,
    "termination_reason": "company_layoff",
    "prior_earnings_annual": 45000,
    "available_for_work": true,
    "actively_seeking_work": true,
    "refused_suitable_work": false
  },
  "policy_context": "State unemployment eligibility requirements:\n1. Minimum 12 months employment\n2. Involuntary separation...",
  "require_consensus": true
}
```

**Response (201 Created):**
```json
{
  "decision_id": "dec_20250115_103045_unemp_001",
  "status": "completed",
  "final_decision": "approved",
  "consensus_analysis": {
    "agreement_level": 1.0,
    "majority_decision": "approved",
    "dissenting_models": [],
    "confidence_variance": 0.0012,
    "reasoning_divergence": null
  },
  "model_decisions": [
    {
      "model_provider": "anthropic",
      "model_name": "claude-3-opus-20240229",
      "decision": "approved",
      "reasoning": "Applicant meets all eligibility criteria...",
      "confidence": 0.95,
      "tokens_used": 1250,
      "latency_ms": 2340
    },
    // ... other models
  ],
  "requires_human_review": false,
  "audit_hash": "a1b2c3d4e5f6..."
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/v1/decisions \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "test_001",
    "decision_type": "unemployment_benefits",
    "input_data": {
      "employment_duration_months": 18,
      "termination_reason": "company_layoff",
      "prior_earnings_annual": 45000,
      "available_for_work": true,
      "actively_seeking_work": true
    },
    "policy_context": "Unemployment eligibility rules...",
    "require_consensus": true
  }'
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/decisions",
    json={
        "case_id": "test_001",
        "decision_type": "unemployment_benefits",
        "input_data": {
            "employment_duration_months": 18,
            "termination_reason": "company_layoff",
            "prior_earnings_annual": 45000,
            "available_for_work": True,
            "actively_seeking_work": True
        },
        "policy_context": "Unemployment eligibility rules...",
        "require_consensus": True
    }
)

decision = response.json()
print(f"Decision: {decision['final_decision']}")
print(f"Consensus: {decision['consensus_analysis']['agreement_level']:.0%}")
```

---

### Get Decision

```http
GET /api/v1/decisions/{decision_id}
```

**Response:**
```json
{
  "decision": {
    "decision_id": "dec_20250115_103045_unemp_001",
    "case_id": "unemp_001",
    "decision_type": "unemployment_benefits",
    "final_decision": "approved",
    "status": "completed",
    "created_at": "2025-01-15T10:30:45Z",
    "completed_at": "2025-01-15T10:30:47Z",
    // ... full decision object
  },
  "audit_verified": true,
  "foia_report": {
    "decision_id": "dec_20250115_103045_unemp_001",
    "case_id": "unemp_001",
    "decision_type": "unemployment_benefits",
    "final_decision": "approved",
    "consensus_level": 1.0,
    "bias_detected": false,
    "human_reviewed": false,
    "audit_hash": "a1b2c3d4..."
  }
}
```

**Use Cases:**
- Retrieve decision details
- Verify audit hash
- Generate FOIA reports
- Display to applicants

---

### List Decisions

```http
GET /api/v1/decisions?status=requires_review&limit=50
```

**Query Parameters:**
- `status` (optional): Filter by status (completed, requires_review, pending)
- `decision_type` (optional): Filter by type (unemployment_benefits, etc.)
- `limit` (optional): Max results (default 100)

**Response:**
```json
{
  "total": 150,
  "filtered": 12,
  "decisions": [
    {
      "decision_id": "dec_20250115_103045_unemp_001",
      "case_id": "unemp_001",
      "decision_type": "unemployment_benefits",
      "final_decision": "approved",
      "status": "completed",
      "created_at": "2025-01-15T10:30:45Z",
      "requires_review": false,
      "consensus_level": 1.0
    },
    // ... more decisions
  ]
}
```

---

## 🔒 Decision Types & Safety

### Unemployment Benefits

```json
{
  "decision_type": "unemployment_benefits",
  "input_data": {
    "employment_duration_months": 18,
    "termination_reason": "company_layoff",  // or "voluntary_resignation", "fired_for_cause"
    "prior_earnings_annual": 45000,
    "available_for_work": true,
    "actively_seeking_work": true,
    "refused_suitable_work": false
  }
}
```

**Safety Triggers:**
- Low consensus (<66%)
- Protected attribute mentioned
- Low confidence (<70%)

---

### Immigration (HIGH-STAKES)

```json
{
  "decision_type": "immigration_deportation",
  "input_data": {
    "visa_status": "expired",
    "entry_date": "2015-03-15",
    "criminal_record": "minor_traffic_violation",
    "family_ties": "spouse_and_children_us_citizens"
  }
}
```

**Safety Triggers:**
- **ALWAYS requires human review** (mandatory)
- Decision type = life-altering
- Protected attributes
- Low consensus

---

## 🛡️ Bias Detection

The API automatically runs bias detection on every decision.

**What Gets Flagged:**

1. **Protected Attributes Mentioned**
   - Race, age, gender, religion, disability, etc.
   - Even if not used in decision, ANY mention triggers review

2. **Low Confidence**
   - Models agree but aren't confident
   - Suggests missing information or edge case

3. **High-Stakes Decisions**
   - Immigration, deportation, benefit termination
   - Automatically require human review

4. **Conflicting Reasoning**
   - Models agree on decision but for different reasons
   - High confidence variance

**Example Flagged Response:**
```json
{
  "decision_id": "dec_...",
  "status": "requires_review",
  "final_decision": "approved",
  "requires_human_review": true,
  "bias_analysis": {
    "bias_detected": true,
    "bias_type": "protected_attribute_bias (age)",
    "affected_attributes": ["age"],
    "confidence": 0.3,
    "recommendation": "CRITICAL: Protected attributes mentioned (age). Verify decision is not based on discriminatory factors."
  }
}
```

---

## 📊 Response Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | GET requests successful |
| 201 | Created | Decision successfully created |
| 404 | Not Found | Decision ID doesn't exist |
| 500 | Server Error | Internal error (check logs) |
| 503 | Service Unavailable | API not ready / no providers |

---

## 🔐 Audit Hash Verification

Every decision includes a SHA-256 audit hash for tamper detection.

**Verifying Integrity:**
```python
# Get decision
response = requests.get(f"{API}/decisions/{decision_id}")
data = response.json()

# Check audit verification
if data['audit_verified']:
    print("✅ Decision has not been tampered with")
else:
    print("❌ AUDIT FAILURE: Decision may be compromised")
```

**Why This Matters:**
- FOIA compliance
- Legal defensibility
- Detect unauthorized modifications
- Chain of custody

---

## 🌐 Integration Examples

### JavaScript/TypeScript (Frontend)

```typescript
async function submitDecision(caseData: any) {
  const response = await fetch('http://localhost:8000/api/v1/decisions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(caseData)
  });

  const decision = await response.json();

  if (decision.requires_human_review) {
    // Route to human reviewer
    routeToReview(decision);
  } else {
    // Auto-approved/denied
    notifyApplicant(decision);
  }
}
```

### Python (Backend Service)

```python
import requests

class TrustChainClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def submit_case(self, case_id, decision_type, data, policy):
        response = requests.post(
            f"{self.base_url}/api/v1/decisions",
            json={
                "case_id": case_id,
                "decision_type": decision_type,
                "input_data": data,
                "policy_context": policy,
                "require_consensus": True
            }
        )
        return response.json()

# Usage
client = TrustChainClient()
decision = client.submit_case(
    case_id="app_001",
    decision_type="unemployment_benefits",
    data={...},
    policy="..."
)
```

---

## 🚨 Error Handling

**Service Unavailable:**
```json
{
  "detail": "Service not ready - orchestrator not initialized"
}
```
**Action:** Check environment variables, ensure API keys are set

**All Providers Failed:**
```json
{
  "detail": "Decision processing failed: All AI providers failed to respond"
}
```
**Action:** Check provider health endpoint, verify API keys

**Invalid Request:**
```json
{
  "detail": [
    {
      "loc": ["body", "case_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
**Action:** Check request format against schema

---

## 📈 Performance

**Typical Response Times:**
- Health check: <10ms
- Decision (3 models in parallel): 2-4 seconds
- Decision (1 model): 2-3 seconds
- Retrieval: <50ms

**Throughput:**
- Limited by AI provider rate limits
- Anthropic: ~50 requests/minute
- OpenAI: ~500 requests/minute
- Llama (local): No limit (hardware dependent)

**Optimization:**
- Responses cached in memory (will use Redis in production)
- Parallel model execution (3x speedup)
- Async I/O throughout

---

## 🔧 Configuration

Set in `.env` file:

```bash
# AI Provider API Keys
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
OLLAMA_BASE_URL=http://localhost:11434

# Consensus Settings
CONSENSUS_THRESHOLD=0.66  # 66% agreement required

# Server Settings
LOG_LEVEL=INFO
DEBUG=True
```

---

## 📚 Next Steps

1. **Start the server**: `uvicorn app:app --reload`
2. **Run tests**: `python test_api.py`
3. **Explore docs**: http://localhost:8000/docs
4. **Build frontend**: Connect React/Vue/etc to API
5. **Add database**: Replace in-memory storage with PostgreSQL

---

## 🎯 Production Checklist

Before deploying to production:

- [ ] Replace in-memory storage with database
- [ ] Add authentication (JWT tokens)
- [ ] Enable rate limiting
- [ ] Restrict CORS to specific origins
- [ ] Set up monitoring/alerting
- [ ] Configure logging to files
- [ ] Add request ID tracking
- [ ] Implement retry logic for failed decisions
- [ ] Set up backup/recovery
- [ ] Load test with expected traffic

---

**Questions?** Check the [main README](README.md) or [Safety Safeguards](../SAFETY_SAFEGUARDS.md) documentation.

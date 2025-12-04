# TrustChain

**Multi-Model AI Decision-Making with Built-in Accountability**

TrustChain is a production-ready AI platform designed for high-stakes government decisions (unemployment benefits, visa approvals, etc.). It solves the "black box" problem by running decisions through multiple AI models and enforcing strict bias detection safeguards.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)

---

## 🎯 The Problem

Government AI decisions today are:
- **Opaque**: Single models with no transparency
- **Risky**: No consensus mechanism to catch errors
- **Biased**: Hidden discrimination in "black box" algorithms
- **Unaccountable**: No audit trails for FOIA requests

## ✨ The Solution

TrustChain provides:
- ✅ **Multi-Model Consensus**: Claude, GPT-4, Llama + any custom LLM you add
- ✅ **Extensible Architecture**: Easy plugin system for Gemini, Cohere, or proprietary models
- ✅ **5-Layer Bias Detection**: Scans for protected attributes, confidence issues, and safety triggers
- ✅ **Immutable Audit Trails**: SHA-256 hashing for tamper detection (FOIA compliant)
- ✅ **Mandatory Human Review**: High-stakes decisions always require human judgment
- ✅ **Full Transparency**: Complete reasoning from every AI model
- ✅ **Commercial-Ready**: Dual licensing (Apache 2.0 for government, commercial license available)

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/Kcheesee/TrustChain.git
cd TrustChain

# Set up environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your API keys

# Start with Docker
docker-compose up -d

# Check health
curl http://localhost:8000/api/v1/health
```

**See [DOCKER_SETUP.md](./DOCKER_SETUP.md) for detailed Docker instructions.**

### Option 2: Manual Setup

```bash
# Prerequisites
# - Python 3.11+
# - PostgreSQL 14+ (optional for v1.1)
# - At least one AI API key (Anthropic or OpenAI)

# Clone and setup
git clone https://github.com/Kcheesee/TrustChain.git
cd TrustChain/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### Run Tests

```bash
# Run pytest suite (recommended)
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest backend/tests/test_bias_detection.py

# Run legacy test scripts
python test_orchestrator.py
```

### Start API Server

```bash
# Development mode
uvicorn app:app --reload

# Production mode
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

Visit **http://localhost:8000/docs** for interactive API documentation.

---

## 📊 Architecture

![Architecture Diagram](ARCHITECTURE_DIAGRAM.md)

### Modular Plugin Architecture (Phase 1 - NEW!)

TrustChain now features a modular plugin architecture with three types of components:

```
TrustChain/backend/
├── core/                     # Core abstractions
│   ├── base.py              # BaseStrategy, BaseAnalyzer, BaseOutput
│   ├── result.py            # StrategyResult, AnalysisResult, AccountabilityResult
│   ├── registry.py          # Plugin registration system
│   └── config.py            # YAML configuration loader
│
├── strategies/              # HOW accountability is established
│   └── multi_model_consensus.py
│
├── analyzers/               # WHAT to check for
│   ├── protected_attributes.py
│   └── proxy_variables.py
│
├── outputs/                 # WHO gets what format
│   ├── internal_audit.py
│   └── consumer_explanation.py
│
├── feedback/                # Phase 3: Human feedback capture
│   ├── capture.py           # HumanFeedback, ReviewerAction enums
│   └── storage.py           # InMemory + SQLite stores
│
├── learning/                # Phase 3: Learning from feedback
│   ├── engine.py            # LearningEngine, LearnedParameters
│   └── safeguards.py        # LearningGuard, bad actor protection
│
├── configs/                 # YAML configuration files
│   ├── unemployment_benefits.yaml
│   ├── hiring.yaml
│   └── immigration.yaml
│
└── services/
    ├── trustchain.py        # Main entry point
    └── orchestrator.py      # Legacy (still supported)
```

**High-Level Flow:**
1. **User submits case** → FastAPI endpoint (v1 or v2)
2. **Load configuration** → YAML-based strategy/analyzer/output selection
3. **Run strategies** → Multi-model consensus, criteria decomposition, etc.
4. **Run analyzers** → Bias detection, confidence calibration, etc.
5. **Generate outputs** → Internal audit, consumer explanation, etc.
6. **Generate audit hash** → SHA-256 for tamper detection
7. **Return decision** → Auto-approve OR flag for human review

---

## 🛡️ Safety Features

### 1. Protected Attribute Detection
Scans every AI response for mentions of:
- Race/Ethnicity
- Age
- Gender
- Religion
- Disability
- Sexual Orientation
- National Origin
- Pregnancy
- Veteran Status

**Action**: ANY mention triggers mandatory human review.

### 2. Confidence Thresholds
- Requires 70%+ average confidence across models
- Low confidence = uncertain = human should decide

### 3. Consensus Quality Analysis
- Measures agreement level (% of models agreeing)
- Calculates confidence variance (are models equally confident?)
- Detects reasoning divergence (same decision, different reasons?)

### 4. Decision Type Classification
- **🔴 Critical**: Immigration, deportation → ALWAYS human review
- **🟡 High-Stakes**: Unemployment, loans → Strict thresholds
- **🟢 Low-Stakes**: Form validation → Can auto-process

### 5. Mandatory Review Triggers
Hard stops that override all other logic:
- Protected attribute detected
- Life-altering decision type
- Very low consensus (<50%)
- Low consensus + bias indicators

---

## 🔄 Feedback & Learning System (Phase 3)

TrustChain learns from human reviewers while protecting against bad actors:

### Human Feedback Loop
```
AI Decision → Human Review → Feedback Captured → Learning Engine → Improved Weights
```

### Feedback Types
- **AGREE**: Human confirms AI decision was correct
- **OVERRIDE_TO_APPROVE**: Human overrides denial → approval
- **OVERRIDE_TO_DENY**: Human overrides approval → denial
- **ESCALATE**: Send to senior reviewer

### Bad Actor Safeguards
| Protection | Description |
|------------|-------------|
| **Reviewer Credibility** | Scored by real-world outcomes, not opinions |
| **Anomaly Detection** | Flags unusual override patterns (>40% rate) |
| **Outcome-Gated Learning** | Waits for reality (90 days) before trusting feedback |
| **Influence Caps** | No single reviewer exceeds 15% of learning weight |
| **Parameter Versioning** | Rollback capability if corruption detected |

### Feedback API Endpoints
```bash
# Submit human feedback
POST /api/v2/feedback

# Record real-world outcome (ground truth)
POST /api/v2/feedback/outcome

# Trigger learning cycle
POST /api/v2/learn

# View safeguards report
GET /api/v2/safeguards/report

# Rollback to previous parameters
POST /api/v2/safeguards/rollback/{version}
```

---

## 📡 API Examples

### V2 API (NEW - Recommended)

The v2 API uses the modular plugin architecture with YAML configuration:

```bash
# Submit evaluation with config
curl -X POST http://localhost:8000/api/v2/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "unemp_001",
    "decision_type": "unemployment_benefits",
    "input_data": {
      "employment_duration_months": 18,
      "termination_reason": "company_layoff",
      "prior_earnings_annual": 45000,
      "available_for_work": true,
      "actively_seeking_work": true
    },
    "config_name": "unemployment_benefits"
  }'
```

### V2 Response

```json
{
  "result_id": "tc_20250124_103045_abc12345",
  "case_id": "unemp_001",
  "decision_type": "unemployment_benefits",
  "final_decision": "approved",
  "overall_confidence": 0.88,
  "requires_human_review": false,
  "review_triggers": [],
  "strategy_result": {
    "strategy_name": "multi_model_consensus",
    "decision": "approved",
    "confidence": 0.88,
    "agreement_level": 1.0
  },
  "analysis_results": [
    {
      "analyzer_name": "protected_attributes",
      "passed": true,
      "flags": [],
      "warnings": []
    }
  ],
  "audit_hash": "a1b2c3d4e5f6..."
}
```

### V2 Additional Endpoints

```bash
# List registered components
curl http://localhost:8000/api/v2/components

# List available configs
curl http://localhost:8000/api/v2/configs

# Validate a config
curl http://localhost:8000/api/v2/configs/unemployment_benefits
```

### V1 API (Legacy - Still Supported)

```bash
curl -X POST http://localhost:8000/api/v1/decisions \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "unemp_001",
    "decision_type": "unemployment_benefits",
    "input_data": {
      "employment_duration_months": 18,
      "termination_reason": "company_layoff",
      "prior_earnings_annual": 45000,
      "available_for_work": true,
      "actively_seeking_work": true
    },
    "policy_context": "State unemployment eligibility requirements...",
    "require_consensus": true
  }'
```

### V1 Response

```json
{
  "decision_id": "dec_20250115_103045_unemp_001",
  "status": "completed",
  "final_decision": "approved",
  "consensus_analysis": {
    "agreement_level": 1.0,
    "majority_decision": "approved",
    "dissenting_models": [],
    "confidence_variance": 0.0012
  },
  "model_decisions": [
    {
      "model_provider": "anthropic",
      "model_name": "claude-3-haiku-20240307",
      "decision": "approved",
      "reasoning": "Applicant meets all eligibility criteria...",
      "confidence": 0.95
    }
  ],
  "requires_human_review": false,
  "audit_hash": "a1b2c3d4e5f6..."
}
```

---

## 🎓 Use Cases

### Unemployment Benefits
- **Input**: Employment history, termination reason, availability
- **Output**: APPROVE/DENY with full reasoning
- **Safety**: Flags low confidence or protected attribute mentions

### Immigration Decisions
- **Input**: Visa status, family ties, criminal record
- **Output**: ALWAYS requires human review (life-altering)
- **Safety**: Mandatory review regardless of consensus

### Loan Approvals
- **Input**: Credit score, income, debt-to-income ratio
- **Output**: Decision with bias detection
- **Safety**: Prevents discrimination based on protected attributes

---

## 📈 Performance

- **Latency**: 2-4 seconds (parallel) vs 6-9 seconds (sequential)
- **Speedup**: 3x faster with parallel execution
- **Reliability**: Works with 1/3 providers if others fail
- **Scalability**: Stateless architecture, horizontal scaling ready

---

## 🔒 Compliance

### FOIA (Freedom of Information Act)
- ✅ Complete audit trails with timestamps
- ✅ SHA-256 hashing for tamper detection
- ✅ PII-stripped public reports
- ✅ 7-year retention configuration

### Civil Rights
- ✅ Protected attribute detection
- ✅ Bias flagging and reporting
- ✅ Mandatory review for discriminatory indicators
- ✅ Full transparency in decision-making

### Data Privacy
- ✅ API keys in environment variables
- ✅ No hardcoded credentials
- ✅ Optional local inference (Llama via Ollama)
- ✅ Audit logs for accountability

---

## 🛠️ Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (REST API)
- Pydantic (data validation)
- AsyncIO (parallel execution)
- PostgreSQL (production database)
- Docker (containerization)

**AI Providers (Built-in):**
- Anthropic (Claude Haiku/Sonnet/Opus)
- OpenAI (GPT-4/GPT-4o)
- Ollama (Local Llama 2/3)

**Extensible Plugin System:**
- Easy integration for Gemini, Cohere, Mistral, etc.
- Custom/proprietary LLM support
- Provider registry for dynamic discovery

---

## 🔌 Adding Custom LLM Providers

TrustChain makes it easy to add support for any LLM:

```python
# 1. Create your provider (5 minutes)
from providers import BaseLLMProvider, register_provider

class GeminiProvider(BaseLLMProvider):
    async def generate_decision(self, prompt, **kwargs):
        # Your API call here
        response = await self.client.generate(prompt)
        return LLMResponse(...)

# 2. Register it
register_provider("gemini", GeminiProvider, metadata={
    "description": "Google Gemini Pro",
    "commercial_use": True
})

# 3. Use in decisions
from providers import get_global_registry

registry = get_global_registry()
provider = registry.create_provider("gemini", config)
```

**Full Guide:** See [CUSTOM_PROVIDERS.md](CUSTOM_PROVIDERS.md) for complete documentation with examples.

**Commercial Support:** Need help integrating a new provider? We offer professional integration services. See [LICENSE_COMMERCIAL.md](LICENSE_COMMERCIAL.md).

---

## 📚 Documentation

**Core Documentation:**
- [Architecture Diagram](ARCHITECTURE_DIAGRAM.md) - Visual system flow
- [Safety Safeguards](SAFETY_SAFEGUARDS.md) - Bias detection deep dive
- [Docker Setup Guide](DOCKER_SETUP.md) - Production deployment
- [Complete MVP Guide](COMPLETE_MVP_GUIDE.md) - End-to-end usage

**Developer Guides:**
- [Custom Providers](CUSTOM_PROVIDERS.md) - Add new LLM integrations
- [API Reference](backend/API_GUIDE.md) - REST API documentation
- [Testing Guide](backend/README.md) - Running tests

**Commercial:**
- [Commercial Licensing](LICENSE_COMMERCIAL.md) - Enterprise options
- [Future Improvements](FUTURE_IMPROVEMENTS.md) - Roadmap

---

## 🧪 Testing

```bash
# Provider connectivity
python test_providers.py

# Single provider (Anthropic only)
python test_single_provider.py

# Full orchestrator
python test_orchestrator_anthropic_only.py

# Bias detection demo
python test_bias_detection.py

# API integration
python test_api.py
```

---

## 🚧 Roadmap

### Completed ✅
- [x] Multi-model orchestrator
- [x] Bias detection system
- [x] Audit trail with hashing
- [x] REST API with Swagger docs
- [x] Test suite
- [x] **Phase 1: Modular Plugin Architecture**
  - [x] Core abstractions (BaseStrategy, BaseAnalyzer, BaseOutput)
  - [x] Plugin registry system
  - [x] YAML configuration loader
  - [x] TrustChain service (v2 API)
  - [x] Multi-model consensus strategy
  - [x] Protected attributes analyzer
  - [x] Internal audit output generator
- [x] **Phase 2: Additional Components**
  - [x] Proxy variables analyzer
  - [x] Consumer explanation output
  - [x] Additional YAML configs (hiring, immigration)
- [x] **Phase 3: Feedback & Learning System**
  - [x] Human feedback capture (agree/override/escalate)
  - [x] Feedback storage (in-memory + SQLite)
  - [x] Learning engine (model weights, confidence calibration)
  - [x] Bad actor safeguards (credibility scoring, anomaly detection)
  - [x] Outcome-gated learning (reality > opinions)
  - [x] Parameter versioning with rollback
- [x] **Phase 4: PostgreSQL Database Integration**
  - [x] SQLAlchemy ORM models
  - [x] Repository pattern implementation
  - [x] Database connection pooling
  - [x] Immutable audit log storage
  - [x] FOIA-compliant data retention
- [x] **Phase 5: Enhanced Fairness Testing**
  - [x] Counterfactual fairness testing
  - [x] Demographic parity analysis
  - [x] Individual fairness validation
  - [x] Context-aware bias detection
- [x] **Phase 6: Safety Monitoring & Real-time Dashboard**
  - [x] Real-time bias rate tracking
  - [x] Consensus degradation alerts
  - [x] Circuit breaker pattern for provider health
  - [x] WebSocket streaming for live updates
  - [x] Alert severity classification
  - [x] 48/48 tests passing (100%)

### In Progress 🚧
- [ ] Frontend dashboard (React/Next.js)
- [ ] JWT authentication
- [ ] Admin panel for human review queue

### Planned 📅 (Phase 7+)
- [ ] Additional strategies (criteria decomposition, adversarial review)
- [ ] LIME/SHAP explainability
- [ ] Demographic blind testing
- [ ] Kubernetes deployment
- [ ] CI/CD pipeline
- [ ] Production monitoring (Datadog/New Relic)

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

Built with:
- [Anthropic Claude](https://www.anthropic.com/) - AI safety-focused models
- [OpenAI GPT](https://openai.com/) - Advanced language models
- [Ollama](https://ollama.ai/) - Local LLM inference
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework

---

**Built for high-stakes government AI decisions with accountability and transparency.**

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
- ✅ **Multi-Model Consensus**: Claude, GPT-4, and Llama evaluate every decision
- ✅ **5-Layer Bias Detection**: Scans for protected attributes, confidence issues, and safety triggers
- ✅ **Immutable Audit Trails**: SHA-256 hashing for tamper detection (FOIA compliant)
- ✅ **Mandatory Human Review**: High-stakes decisions always require human judgment
- ✅ **Full Transparency**: Complete reasoning from every AI model

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- At least one AI API key (Anthropic or OpenAI)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/trustchain.git
cd trustchain/backend

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
# Test individual providers
python test_single_provider.py

# Test full orchestrator
python test_orchestrator_anthropic_only.py

# Test bias detection
python test_bias_detection.py
```

### Start API Server

```bash
uvicorn app:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

---

## 📊 Architecture

![Architecture Diagram](ARCHITECTURE_DIAGRAM.md)

**High-Level Flow:**
1. **User submits case** → FastAPI endpoint
2. **Orchestrator queries 3 AI models** → Parallel execution (Claude, GPT-4, Llama)
3. **Parse responses** → Extract decisions + reasoning
4. **Analyze consensus** → Agreement level, confidence variance
5. **Run bias detection** → 5-layer safety checks
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

## 📡 API Examples

### Submit Decision

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

### Response

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

**AI Providers:**
- Anthropic (Claude Haiku/Sonnet/Opus)
- OpenAI (GPT-4/GPT-4o)
- Ollama (Local Llama 2/3)

**Future:**
- PostgreSQL (persistent storage)
- Redis (caching)
- React (frontend dashboard)
- Docker (containerization)

---

## 📚 Documentation

- [Architecture Diagram](ARCHITECTURE_DIAGRAM.md) - Visual system flow
- [API Guide](backend/API_GUIDE.md) - REST API reference
- [Safety Safeguards](SAFETY_SAFEGUARDS.md) - Bias detection deep dive
- [Backend README](backend/README.md) - Technical setup
- [Interview FAQ](INTERVIEW_FAQ.md) - Talking points for recruiters

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

### In Progress 🚧
- [ ] PostgreSQL integration
- [ ] Frontend dashboard (React)
- [ ] JWT authentication

### Planned 📅
- [ ] WebSocket support (real-time updates)
- [ ] Advanced consensus algorithms (weighted voting)
- [ ] LIME/SHAP explainability
- [ ] Demographic blind testing
- [ ] Docker deployment

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

## 📞 Contact

**Kareem** - AI Engineer transitioning from government consulting

- Portfolio: [your-portfolio.com]
- LinkedIn: [linkedin.com/in/yourprofile]
- Email: [your-email@example.com]

---

**Built with care to demonstrate technical excellence and deep understanding of government AI compliance requirements.**

*Perfect for roles at Anthropic, OpenAI, and other AI safety-focused organizations.* 🚀

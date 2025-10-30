# TrustChain Backend

Multi-model AI decision-making system with government compliance and FOIA transparency.

## Architecture Overview

TrustChain solves the "black box" problem in government AI decisions by:
1. Running decisions through multiple AI models (Claude, GPT-4, Llama)
2. Creating consensus decisions with full reasoning trails
3. Maintaining immutable audit logs for FOIA compliance
4. Detecting and reporting potential bias

## Project Structure

```
backend/
├── providers/              # LLM provider implementations
│   ├── base.py            # Abstract provider with retry logic
│   ├── anthropic_provider.py
│   ├── openai_provider.py
│   └── llama_provider.py
├── models/                # Data models and validation
│   ├── decision.py        # Decision models with audit hashing
│   ├── audit.py          # (Coming soon)
│   └── compliance.py     # (Coming soon)
├── services/              # Business logic (Coming soon)
│   ├── orchestrator.py   # Multi-model coordinator
│   ├── consensus.py      # Consensus algorithm
│   └── audit_chain.py    # Immutable audit logging
├── database/              # Database schemas (Coming soon)
│   └── schema.sql
└── app.py                # FastAPI application (Coming soon)
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required API keys:
- **Anthropic**: Get from https://console.anthropic.com
- **OpenAI**: Get from https://platform.openai.com

### 3. Install Ollama (for local Llama)

```bash
# macOS
brew install ollama

# Linux
curl https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull a model
ollama pull llama2:13b
```

### 4. Test Providers

```bash
python test_providers.py
```

You should see:
```
✅ ANTHROPIC : PASSED
✅ OPENAI    : PASSED
✅ LLAMA     : PASSED

🎉 All providers operational!
```

## Provider System Design

### Abstract Base Provider

All providers inherit from `BaseLLMProvider` which provides:

- **Automatic retry logic** with exponential backoff
- **Health monitoring** and error rate tracking
- **Timeout handling** for all API calls
- **Standardized responses** via `LLMResponse` dataclass
- **Audit logging** for government compliance

### Provider Implementations

#### Anthropic (Claude)
- Uses latest Claude Opus model
- Extracts structured reasoning from responses
- Confidence scoring based on language certainty

#### OpenAI (GPT-4)
- Uses GPT-4o for best performance
- Similar confidence calculation to Claude
- Handles OpenAI's chat completion format

#### Llama (Ollama)
- Local inference for sensitive data
- No external API calls (critical for government)
- Slightly lower confidence scores (typical for local models)

## Key Features for Government Use

### 1. Immutable Audit Trail
Every decision gets a SHA-256 hash:
```python
decision = Decision(...)
decision.audit_hash = decision.calculate_audit_hash()

# Later, verify integrity
is_valid = decision.verify_audit_hash()  # True if not tampered
```

### 2. FOIA Compliance
Strip PII while maintaining transparency:
```python
foia_report = decision.to_foia_report()
# Returns public-record-safe version
```

### 3. Multi-Model Consensus
Reduce bias and increase reliability:
```python
# Get decisions from all 3 models
anthropic_decision = await anthropic_provider.generate_decision(...)
openai_decision = await openai_provider.generate_decision(...)
llama_decision = await llama_provider.generate_decision(...)

# Analyze consensus (orchestrator handles this)
```

### 4. Bias Detection
Flag potential bias for human review:
```python
bias_analysis = BiasDetection(
    bias_detected=True,
    bias_type="socioeconomic",
    recommendation="Human review recommended"
)
```

## Error Handling

All providers use the same error handling pattern:

```python
try:
    response = await provider.generate_decision(prompt, context)
except ProviderException as e:
    if e.recoverable:
        # Retry or route to different provider
        pass
    else:
        # Fail gracefully, log for human review
        pass
```

## Response Format

All providers return standardized `LLMResponse`:

```python
LLMResponse(
    provider=ModelProvider.ANTHROPIC,
    model_name="claude-3-opus-20240229",
    content="APPROVED - Applicant meets all criteria...",
    reasoning="Step-by-step analysis: 1. Employment duration...",
    confidence=0.85,
    tokens_used=1250,
    latency_ms=2340.5,
    metadata={...}
)
```

## Next Steps

### Week 1 Remaining Tasks:
1. **Orchestrator Service** - Coordinate multiple providers
2. **Consensus Algorithm** - Analyze agreement/disagreement
3. **FastAPI Application** - REST API endpoints
4. **Database Schema** - PostgreSQL audit tables
5. **Unemployment Benefits Demo** - Complete end-to-end example

### Week 2+ Features:
- Frontend React visualization
- Real-time decision streaming
- Admin dashboard for human review
- Bias detection algorithms
- Performance monitoring

## Testing

Test individual providers:
```bash
python test_providers.py
```

Test orchestrator (coming soon):
```bash
pytest tests/test_orchestrator.py
```

Full integration test (coming soon):
```bash
pytest tests/test_integration.py
```

## Government Compliance Features

- ✅ FOIA-compliant audit trails
- ✅ Immutable decision records (SHA-256 hashing)
- ✅ PII protection in public records
- ✅ 7-year log retention configuration
- ✅ Multi-model consensus for fairness
- ⏳ Bias detection (in progress)
- ⏳ Human review workflow (planned)

## Performance Considerations

- All I/O operations use async/await
- Connection pooling for database
- Provider health monitoring routes around failures
- Local Llama option for sensitive data (no external calls)

## Security

- API keys in environment variables (never committed)
- JWT authentication for API endpoints
- Input validation via Pydantic
- SQL injection prevention (parameterized queries)
- Rate limiting on API endpoints

## License

MIT License - See LICENSE file

## Contact

For questions or contributions, see CONTRIBUTING.md

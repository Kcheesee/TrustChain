# TrustChain Accountability & Audit Trail System

## 🔍 Core Accountability Features

TrustChain maintains **complete transparency** for every decision through:

1. **Immutable Audit Logs** - Cryptographically secured, tamper-proof records
2. **Full Decision Lineage** - Track every step from input to final decision
3. **FOIA Compliance** - Government-ready transparency
4. **Human Review Trail** - Track who reviewed what and why

---

## 🗄️ What Gets Recorded

### Every Decision Includes:

```python
{
    "decision_id": "dec_2025_001234",
    "timestamp": "2025-01-15T10:30:00Z",
    
    # Input data (what was considered)
    "input_data": {
        "applicant_id": "anon_987654",
        "case_type": "unemployment_benefits",
        "employment_duration_months": 18,
        "termination_reason": "layoff",
        "prior_earnings": 45000
    },
    
    # All AI model responses
    "model_decisions": [
        {
            "provider": "anthropic",
            "model": "claude-3-opus",
            "decision": "approved",
            "reasoning": "Applicant meets all eligibility criteria...",
            "confidence": 0.95,
            "timestamp": "2025-01-15T10:30:02Z"
        },
        {
            "provider": "openai",
            "model": "gpt-4",
            "decision": "approved",
            "reasoning": "Clear case of involuntary termination...",
            "confidence": 0.88,
            "timestamp": "2025-01-15T10:30:03Z"
        },
        {
            "provider": "llama",
            "model": "llama-3-70b",
            "decision": "approved",
            "reasoning": "Eligible based on work history...",
            "confidence": 0.82,
            "timestamp": "2025-01-15T10:30:04Z"
        }
    ],
    
    # Consensus analysis
    "consensus": {
        "agreement_level": 1.0,  # 100% agreement
        "weighted_agreement": 0.95,
        "majority_decision": "approved",
        "dissenting_models": [],
        "confidence_variance": 0.0041
    },
    
    # Bias detection results
    "bias_analysis": {
        "bias_detected": false,
        "protected_attributes_found": [],
        "safety_triggers": [],
        "requires_human_review": false,
        "recommendation": "No bias indicators detected"
    },
    
    # Fairness test results
    "fairness_tests": [
        {
            "test_type": "demographic_parity",
            "passed": true,
            "fairness_score": 0.98
        }
    ],
    
    # Final decision
    "final_decision": "approved",
    "status": "completed",
    
    # Cryptographic proof
    "audit_hash": "a1b2c3d4e5f6789...",  # SHA-256 hash
    
    # Human review (if applicable)
    "human_review": null  # or review details if flagged
}
```

---

## 🔐 Immutable Audit Trail

### How It Works

```python
# 1. Every event is logged
audit_log = {
    "event_type": "decision_created",
    "decision_id": "dec_2025_001234",
    "timestamp": "2025-01-15T10:30:00Z",
    "actor": "system",
    "event_data": {...},
    "event_hash": "sha256_hash_of_event",
    "previous_hash": "sha256_hash_of_previous_event"  # Blockchain-style chaining
}

# 2. Hash is calculated
event_hash = SHA256(
    decision_id + 
    timestamp + 
    event_data + 
    previous_hash
)

# 3. Stored in database (append-only)
# ❌ CANNOT be modified or deleted
# ✅ Database triggers prevent tampering
```

### Database Protection

```sql
-- Trigger prevents audit log modifications
CREATE TRIGGER prevent_audit_modification
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW
EXECUTE FUNCTION raise_exception('Audit logs are immutable');
```

---

## 📊 Audit Trail Examples

### Example 1: Standard Approval

```
Timeline for Decision dec_2025_001234:

10:30:00 - Decision Created
           Actor: API Client (unemployment_office_api)
           Input: Case #987654 submitted

10:30:01 - AI Models Queried
           Actor: System
           Models: Claude, GPT-4, Llama

10:30:02 - Claude Response Received
           Decision: APPROVED
           Confidence: 95%
           Reasoning: "Applicant meets all criteria..."

10:30:03 - GPT-4 Response Received
           Decision: APPROVED
           Confidence: 88%

10:30:04 - Llama Response Received
           Decision: APPROVED
           Confidence: 82%

10:30:05 - Consensus Calculated
           Agreement: 100%
           Weighted Score: 95%

10:30:06 - Bias Detection Run
           Result: No bias detected
           Protected Attributes: None found

10:30:07 - Decision Finalized
           Final Decision: APPROVED
           Status: Completed
           Audit Hash: a1b2c3d4...

✅ Decision completed in 7 seconds
```

### Example 2: Human Review Required

```
Timeline for Decision dec_2025_005678:

14:15:00 - Decision Created
           Case: Immigration visa application

14:15:05 - AI Models Queried

14:15:08 - Bias Detection ALERT
           ⚠️  Protected attribute detected: "national_origin"
           Severity: HIGH
           Recommendation: Mandatory human review

14:15:09 - Decision Flagged for Review
           Status: REQUIRES_REVIEW
           Assigned to: Human Reviewer #42

[2 hours later]

16:30:00 - Human Review Started
           Reviewer: Jane Smith (reviewer_id: 42)
           IP: 192.168.1.100

16:45:00 - Human Review Completed
           Reviewer Decision: APPROVED
           Override Reason: "AI correctly identified eligibility. 
                           National origin mention was contextual 
                           (verifying visa requirements), not discriminatory."
           
16:45:01 - Decision Finalized
           Final Decision: APPROVED
           Status: COMPLETED_WITH_HUMAN_REVIEW
           Audit Hash: x9y8z7...

✅ Decision completed with human oversight
```

### Example 3: Bias Detected & Prevented

```
Timeline for Decision dec_2025_009999:

09:00:00 - Decision Created
           Case: Loan application

09:00:05 - AI Models Queried

09:00:08 - Consensus Analysis
           Agreement: 67%
           2 models: APPROVED
           1 model: DENIED

09:00:09 - Bias Detection ALERT
           🚨 CRITICAL: Age discrimination detected
           Reasoning contained: "applicant is too old at 58"
           Severity: CRITICAL

09:00:10 - Fairness Test FAILED
           Test: Counterfactual Fairness
           Result: Decision changed when age modified
           Violation: Age-based discrimination

09:00:11 - Decision BLOCKED
           Status: REQUIRES_MANDATORY_REVIEW
           Reason: Discrimination detected
           Assigned to: Compliance Team

09:30:00 - Compliance Review Started
           Reviewer: Compliance Officer #7

09:45:00 - Decision REJECTED
           Reviewer Action: DENY the AI recommendation
           Reason: "AI reasoning contained age discrimination.
                   Retraining required. Manual review of 
                   applicant shows they ARE qualified."
           
           Manual Decision: APPROVED (overriding AI)
           
09:45:01 - Incident Logged
           Incident Type: AI_BIAS_DETECTED
           Action Taken: Model flagged for retraining
           
09:45:02 - Decision Finalized
           Final Decision: APPROVED (human override)
           Status: COMPLETED_WITH_OVERRIDE
           Audit Hash: p9q8r7...

✅ Discrimination prevented by safety system
```

---

## 🔎 Audit Queries

### Query 1: Find All Decisions for a Case

```python
from database import get_db, DecisionRepository

with get_db() as db:
    repo = DecisionRepository(db)
    decisions = repo.get_by_case_id("case_987654")
    
    for decision in decisions:
        print(f"Decision: {decision.final_decision}")
        print(f"Date: {decision.created_at}")
        print(f"Audit Hash: {decision.audit_hash}")
```

### Query 2: Get Complete Audit Trail

```python
from database import AuditLogRepository

with get_db() as db:
    audit_repo = AuditLogRepository(db)
    logs = audit_repo.get_by_decision_id("dec_2025_001234")
    
    for log in logs:
        print(f"{log.timestamp} - {log.event_type}")
        print(f"  Actor: {log.actor}")
        print(f"  Hash: {log.event_hash}")
```

### Query 3: Find All Bias Detections

```python
from database import BiasAnalysisRepository

with get_db() as db:
    bias_repo = BiasAnalysisRepository(db)
    flagged = bias_repo.get_flagged_decisions(limit=100)
    
    for bias in flagged:
        print(f"Decision: {bias.decision_id}")
        print(f"Attributes: {bias.protected_attributes_found}")
        print(f"Severity: {bias.severity}")
```

---

## 📋 FOIA Compliance

### Freedom of Information Act Requirements

TrustChain meets all FOIA requirements:

✅ **Complete Records** - Every decision fully documented
✅ **Immutable Storage** - Cannot be altered after creation
✅ **Cryptographic Proof** - Hash verification prevents tampering
✅ **7-Year Retention** - Automatic archival after 7 years
✅ **Searchable** - Indexed by case ID, date, type, etc.
✅ **Exportable** - JSON/PDF export for FOIA requests

### FOIA Request Example

```python
# Generate FOIA report for a decision
def generate_foia_report(decision_id):
    with get_db() as db:
        # Get decision
        decision = DecisionRepository(db).get_by_id(decision_id)
        
        # Get all model decisions
        model_decisions = ModelDecisionRepository(db).get_by_decision_id(decision_id)
        
        # Get bias analysis
        bias = BiasAnalysisRepository(db).get_by_decision_id(decision_id)
        
        # Get audit trail
        audit_logs = AuditLogRepository(db).get_by_decision_id(decision_id)
        
        # Compile report
        report = {
            "decision_summary": {
                "decision_id": decision.decision_id,
                "case_id": decision.case_id,
                "final_decision": decision.final_decision,
                "date": decision.created_at.isoformat(),
                "audit_hash": decision.audit_hash
            },
            "ai_model_responses": [
                {
                    "provider": md.provider,
                    "decision": md.decision,
                    "reasoning": md.reasoning,
                    "confidence": md.confidence
                }
                for md in model_decisions
            ],
            "bias_analysis": {
                "bias_detected": bias.bias_detected,
                "protected_attributes": bias.protected_attributes_found,
                "recommendation": bias.recommendation
            },
            "complete_audit_trail": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "event": log.event_type,
                    "actor": log.actor,
                    "hash": log.event_hash
                }
                for log in audit_logs
            ],
            "verification": {
                "audit_hash_verified": verify_audit_hash(decision),
                "chain_integrity": verify_audit_chain(audit_logs)
            }
        }
        
        return report
```

---

## 🛡️ Tamper Detection

### Hash Verification

```python
def verify_audit_hash(decision):
    """Verify decision hasn't been tampered with."""
    
    # Recalculate hash from current data
    calculated_hash = hashlib.sha256(
        f"{decision.decision_id}"
        f"{decision.final_decision}"
        f"{decision.created_at}"
        f"{json.dumps(decision.input_data)}"
        # ... all decision fields
    ).hexdigest()
    
    # Compare with stored hash
    if calculated_hash != decision.audit_hash:
        raise TamperDetectionError(
            f"Decision {decision.decision_id} has been tampered with!"
        )
    
    return True
```

### Chain Verification

```python
def verify_audit_chain(audit_logs):
    """Verify audit log chain integrity (blockchain-style)."""
    
    for i, log in enumerate(audit_logs[1:], 1):
        previous_log = audit_logs[i-1]
        
        # Verify current log's previous_hash matches previous log's hash
        if log.previous_hash != previous_log.event_hash:
            raise ChainIntegrityError(
                f"Audit chain broken at log {log.id}!"
            )
    
    return True
```

---

## 📈 Accountability Reports

### Monthly Bias Report

```sql
SELECT 
    decision_type,
    COUNT(*) as total_decisions,
    SUM(CASE WHEN bias_detected THEN 1 ELSE 0 END) as bias_detected_count,
    ROUND(AVG(CASE WHEN bias_detected THEN 1 ELSE 0 END) * 100, 2) as bias_rate,
    array_agg(DISTINCT unnest(protected_attributes_found)) as attributes_flagged
FROM decisions d
JOIN bias_analyses b ON d.decision_id = b.decision_id
WHERE d.created_at >= NOW() - INTERVAL '30 days'
GROUP BY decision_type;
```

### Human Override Analysis

```sql
SELECT 
    COUNT(*) as total_reviews,
    SUM(CASE WHEN reviewed_by_human THEN 1 ELSE 0 END) as human_reviewed,
    SUM(CASE WHEN override_reason IS NOT NULL THEN 1 ELSE 0 END) as ai_overridden,
    ROUND(AVG(CASE WHEN override_reason IS NOT NULL THEN 1 ELSE 0 END) * 100, 2) as override_rate
FROM decisions
WHERE created_at >= NOW() - INTERVAL '30 days';
```

---

## 🎯 Key Benefits

### For Government Agencies
- ✅ **FOIA Compliance** - Instant report generation
- ✅ **Legal Defense** - Complete decision justification
- ✅ **Audit Ready** - Always prepared for audits
- ✅ **Accountability** - Track every decision maker

### For Citizens
- ✅ **Transparency** - See exactly why decision was made
- ✅ **Appeal Rights** - Full record for appeals
- ✅ **Trust** - Cryptographic proof of integrity
- ✅ **Fairness** - Bias detection visible

### For Compliance
- ✅ **Tamper-Proof** - Cannot alter historical records
- ✅ **Traceable** - Every action logged
- ✅ **Verifiable** - Hash verification
- ✅ **Searchable** - Quick FOIA responses

---

## 🚀 Summary

**TrustChain's accountability system ensures:**

1. **Every decision is fully documented** - No black boxes
2. **Records are immutable** - Cannot be tampered with
3. **Complete transparency** - FOIA-ready at all times
4. **Bias is tracked** - Discrimination patterns visible
5. **Human oversight is logged** - Reviewers accountable
6. **Cryptographically verified** - Tamper detection built-in

**This is what makes TrustChain different from other AI systems - you can ALWAYS look back and see exactly how and why a decision was made, with mathematical proof it hasn't been altered.** 🔍

---

**"In AI we trust, but we verify."** - TrustChain Philosophy

-- TrustChain Database Schema
-- PostgreSQL 14+
-- Purpose: Store AI decision records with full audit trails for FOIA compliance

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Main decisions table
CREATE TABLE IF NOT EXISTS decisions (
    decision_id VARCHAR(255) PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    case_type VARCHAR(100) NOT NULL,  -- e.g., "unemployment_benefits", "visa_application"
    decision_type VARCHAR(100) NOT NULL,  -- e.g., "critical", "high_stakes", "standard"

    -- Final decision outcome
    final_decision VARCHAR(50),  -- "approve", "deny", "needs_review"
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- "pending", "completed", "reviewed", "appealed"

    -- Consensus metrics
    consensus_level FLOAT,  -- 0.0 to 1.0
    avg_confidence FLOAT,  -- 0.0 to 1.0
    confidence_variance FLOAT,

    -- Audit trail
    audit_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash for tamper detection

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    reviewed_at TIMESTAMP,

    -- Indexes for common queries
    CONSTRAINT valid_consensus CHECK (consensus_level >= 0 AND consensus_level <= 1),
    CONSTRAINT valid_confidence CHECK (avg_confidence >= 0 AND avg_confidence <= 1)
);

CREATE INDEX idx_decisions_case_id ON decisions(case_id);
CREATE INDEX idx_decisions_status ON decisions(status);
CREATE INDEX idx_decisions_created_at ON decisions(created_at DESC);
CREATE INDEX idx_decisions_decision_type ON decisions(decision_type);


-- Individual model decisions
CREATE TABLE IF NOT EXISTS model_decisions (
    id SERIAL PRIMARY KEY,
    decision_id VARCHAR(255) NOT NULL REFERENCES decisions(decision_id) ON DELETE CASCADE,

    -- Model information
    provider VARCHAR(50) NOT NULL,  -- "anthropic", "openai", "llama"
    model_name VARCHAR(100) NOT NULL,  -- "claude-opus-4", "gpt-4", etc.
    model_version VARCHAR(50),

    -- Decision details
    decision VARCHAR(50) NOT NULL,  -- "approve", "deny"
    reasoning TEXT NOT NULL,
    confidence FLOAT NOT NULL,

    -- Metadata
    latency_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    estimated_cost DECIMAL(10, 6),

    -- Timestamps
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_model_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE INDEX idx_model_decisions_decision_id ON model_decisions(decision_id);
CREATE INDEX idx_model_decisions_provider ON model_decisions(provider);
CREATE INDEX idx_model_decisions_timestamp ON model_decisions(timestamp DESC);


-- Bias detection results
CREATE TABLE IF NOT EXISTS bias_analyses (
    id SERIAL PRIMARY KEY,
    decision_id VARCHAR(255) NOT NULL REFERENCES decisions(decision_id) ON DELETE CASCADE,

    -- Bias detection results
    bias_detected BOOLEAN NOT NULL DEFAULT FALSE,
    bias_score FLOAT,  -- 0.0 (no bias) to 1.0 (severe bias)

    -- Protected attributes found
    protected_attributes_found TEXT[],  -- Array of attributes like ["race", "age"]

    -- Safety triggers
    safety_triggers TEXT[],  -- Array of trigger reasons
    requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,

    -- Detailed analysis
    bias_type VARCHAR(100),  -- "protected_attribute", "low_confidence", "low_consensus", etc.
    affected_attributes JSONB,  -- Detailed JSON with context
    recommendation TEXT,

    -- Timestamps
    analyzed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bias_analyses_decision_id ON bias_analyses(decision_id);
CREATE INDEX idx_bias_analyses_bias_detected ON bias_analyses(bias_detected);
CREATE INDEX idx_bias_analyses_requires_review ON bias_analyses(requires_human_review);


-- Audit logs (immutable, append-only)
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    decision_id VARCHAR(255) NOT NULL REFERENCES decisions(decision_id) ON DELETE CASCADE,

    -- Event information
    event_type VARCHAR(100) NOT NULL,  -- "decision_created", "decision_completed", "bias_detected", etc.
    event_details JSONB NOT NULL,

    -- User/system information
    actor VARCHAR(255),  -- Who triggered this event
    actor_type VARCHAR(50),  -- "system", "human_reviewer", "api_client"

    -- IP and request info
    ip_address INET,
    user_agent TEXT,

    -- Timestamp (immutable)
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Cryptographic proof
    event_hash VARCHAR(64) NOT NULL  -- SHA-256 of event data
);

CREATE INDEX idx_audit_logs_decision_id ON audit_logs(decision_id);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor);


-- ============================================================================
-- AUTHENTICATION & AUTHORIZATION (for v1.1)
-- ============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,

    -- Profile
    full_name VARCHAR(255),
    department VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'reviewer',  -- "admin", "reviewer", "api_client"

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,

    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);


-- API keys for programmatic access
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Key information
    key_hash VARCHAR(255) UNIQUE NOT NULL,  -- Hashed API key
    key_prefix VARCHAR(20) NOT NULL,  -- First few chars for identification
    name VARCHAR(255),  -- User-friendly name

    -- Permissions
    scopes TEXT[],  -- Array of permissions like ["decisions:read", "decisions:write"]

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMP,

    -- Expiration
    expires_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_expiration CHECK (expires_at IS NULL OR expires_at > created_at)
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);


-- ============================================================================
-- STATISTICS & MONITORING
-- ============================================================================

-- Provider health metrics
CREATE TABLE IF NOT EXISTS provider_health (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,

    -- Health metrics
    status VARCHAR(50) NOT NULL,  -- "healthy", "degraded", "down"
    success_rate FLOAT,
    avg_latency_ms INTEGER,
    error_count INTEGER DEFAULT 0,

    -- Timestamps
    checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_success_rate CHECK (success_rate >= 0 AND success_rate <= 1)
);

CREATE INDEX idx_provider_health_provider ON provider_health(provider);
CREATE INDEX idx_provider_health_checked_at ON provider_health(checked_at DESC);


-- Decision statistics (aggregated)
CREATE TABLE IF NOT EXISTS decision_stats (
    id SERIAL PRIMARY KEY,

    -- Time period
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,

    -- Aggregated metrics
    total_decisions INTEGER DEFAULT 0,
    total_approvals INTEGER DEFAULT 0,
    total_denials INTEGER DEFAULT 0,
    total_reviews_required INTEGER DEFAULT 0,

    -- Quality metrics
    avg_consensus FLOAT,
    avg_confidence FLOAT,
    bias_detected_count INTEGER DEFAULT 0,

    -- Performance
    avg_processing_time_ms INTEGER,

    -- Timestamps
    computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_period CHECK (period_end > period_start)
);

CREATE INDEX idx_decision_stats_period ON decision_stats(period_start, period_end);


-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Decisions requiring human review
CREATE OR REPLACE VIEW decisions_requiring_review AS
SELECT
    d.decision_id,
    d.case_id,
    d.case_type,
    d.decision_type,
    d.consensus_level,
    d.avg_confidence,
    b.bias_detected,
    b.protected_attributes_found,
    b.safety_triggers,
    d.created_at
FROM decisions d
JOIN bias_analyses b ON d.decision_id = b.decision_id
WHERE b.requires_human_review = TRUE
AND d.status = 'pending'
ORDER BY d.created_at DESC;


-- View: Recent audit trail
CREATE OR REPLACE VIEW recent_audit_trail AS
SELECT
    al.id,
    al.decision_id,
    d.case_id,
    al.event_type,
    al.actor,
    al.actor_type,
    al.timestamp,
    al.event_hash
FROM audit_logs al
JOIN decisions d ON al.decision_id = d.decision_id
ORDER BY al.timestamp DESC
LIMIT 1000;


-- View: Provider performance summary
CREATE OR REPLACE VIEW provider_performance AS
SELECT
    md.provider,
    md.model_name,
    COUNT(*) as total_decisions,
    AVG(md.confidence) as avg_confidence,
    AVG(md.latency_ms) as avg_latency_ms,
    SUM(md.estimated_cost) as total_cost
FROM model_decisions md
WHERE md.timestamp > NOW() - INTERVAL '7 days'
GROUP BY md.provider, md.model_name
ORDER BY total_decisions DESC;


-- ============================================================================
-- FUNCTIONS FOR DATA INTEGRITY
-- ============================================================================

-- Function: Automatically create audit log on decision update
CREATE OR REPLACE FUNCTION log_decision_update()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (decision_id, event_type, event_details, actor_type, event_hash)
    VALUES (
        NEW.decision_id,
        'decision_updated',
        jsonb_build_object(
            'old_status', OLD.status,
            'new_status', NEW.status,
            'old_decision', OLD.final_decision,
            'new_decision', NEW.final_decision
        ),
        'system',
        encode(sha256(NEW.decision_id::bytea || NOW()::text::bytea), 'hex')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Log decision updates
CREATE TRIGGER trigger_log_decision_update
AFTER UPDATE ON decisions
FOR EACH ROW
WHEN (OLD.status IS DISTINCT FROM NEW.status OR OLD.final_decision IS DISTINCT FROM NEW.final_decision)
EXECUTE FUNCTION log_decision_update();


-- Function: Prevent audit log modifications (immutability)
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable and cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

-- Trigger: Prevent audit log updates
CREATE TRIGGER trigger_prevent_audit_update
BEFORE UPDATE ON audit_logs
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_log_modification();

-- Trigger: Prevent audit log deletes
CREATE TRIGGER trigger_prevent_audit_delete
BEFORE DELETE ON audit_logs
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_log_modification();


-- ============================================================================
-- DATA RETENTION POLICY (7 YEARS FOR FOIA COMPLIANCE)
-- ============================================================================

-- Function: Archive old decisions (optional, for performance)
CREATE OR REPLACE FUNCTION archive_old_decisions(retention_days INTEGER DEFAULT 2555)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- This is a placeholder for archival logic
    -- In production, you might move to an archive table or cold storage
    SELECT COUNT(*)
    INTO archived_count
    FROM decisions
    WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL;

    -- Uncomment to actually archive:
    -- INSERT INTO decisions_archive SELECT * FROM decisions WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL;
    -- DELETE FROM decisions WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL;

    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- SEED DATA (for development/testing)
-- ============================================================================

-- Insert default admin user (password: 'changeme' - CHANGE IN PRODUCTION)
INSERT INTO users (username, email, hashed_password, full_name, role, is_active, is_verified)
VALUES (
    'admin',
    'admin@trustchain.gov',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yvT5YIjsJGC.',  -- bcrypt hash of 'changeme'
    'System Administrator',
    'admin',
    TRUE,
    TRUE
)
ON CONFLICT (username) DO NOTHING;


-- ============================================================================
-- COMMENTS & DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE decisions IS 'Main table storing all AI-assisted decisions with consensus metrics';
COMMENT ON TABLE model_decisions IS 'Individual decisions from each AI model (Claude, GPT-4, Llama)';
COMMENT ON TABLE bias_analyses IS 'Bias detection results for each decision, flagging protected attributes and safety concerns';
COMMENT ON TABLE audit_logs IS 'Immutable append-only log of all events for FOIA compliance';
COMMENT ON TABLE users IS 'System users with role-based access control';
COMMENT ON TABLE api_keys IS 'API keys for programmatic access to TrustChain';
COMMENT ON TABLE provider_health IS 'Health monitoring metrics for AI providers';
COMMENT ON TABLE decision_stats IS 'Aggregated statistics for reporting and dashboards';

COMMENT ON COLUMN decisions.audit_hash IS 'SHA-256 hash for tamper detection - validates decision integrity';
COMMENT ON COLUMN bias_analyses.protected_attributes_found IS 'Array of protected attributes (race, gender, age, etc.) found in model reasoning';
COMMENT ON COLUMN audit_logs.event_hash IS 'Cryptographic hash of event data for audit trail verification';


-- ============================================================================
-- GRANTS (adjust for your production environment)
-- ============================================================================

-- Grant appropriate permissions
-- GRANT SELECT, INSERT, UPDATE ON decisions, model_decisions, bias_analyses TO trustchain_app;
-- GRANT SELECT, INSERT ON audit_logs TO trustchain_app;
-- GRANT SELECT ON users, api_keys TO trustchain_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trustchain_app;

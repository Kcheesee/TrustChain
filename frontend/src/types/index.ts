/**
 * TrustChain Dashboard TypeScript Types
 *
 * Type definitions for real-time dashboard data.
 *
 * Built with care by Kareem & Claude
 */

// WebSocket Message Types
export type WebSocketMessageType =
  | "connected"
  | "decision"
  | "metrics"
  | "alert"
  | "reviewer_activity"
  | "fairness_result";

export interface WebSocketMessage {
  type: WebSocketMessageType;
  data?: Record<string, unknown>;
  timestamp: string;
  channels?: string[];
  message?: string;
}

// Decision Types
export interface Decision {
  result_id: string;
  case_id: string;
  decision_type: string;
  final_decision: "approved" | "denied" | "needs_review";
  confidence: number;
  requires_review: boolean;
  review_triggers: string[];
  timestamp: string;
}

// Metrics Summary
export interface MetricsSummary {
  total_decisions: number;
  decisions_approved: number;
  decisions_denied: number;
  decisions_needs_review: number;
  approval_rate: number;
  review_rate: number;
  avg_confidence: number;
  avg_fairness_score: number;
  decisions_with_bias: number;
  bias_rate: number;
  decisions_per_minute: number;
  avg_latency_ms: number;
  window_start: string;
  window_end: string;
}

// Time Series Data
export interface TimeSeriesPoint {
  timestamp: string;
  total: number;
  approved: number;
  denied: number;
  needs_review: number;
}

export interface FairnessTimeSeriesPoint {
  timestamp: string;
  avg_fairness: number | null;
  min_fairness: number | null;
  max_fairness: number | null;
  count: number;
}

// Reviewer Activity
export interface ReviewerActivity {
  reviewer_id: string;
  action: string;
  result_id: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface ReviewerSummary {
  total_activity: number;
  unique_reviewers: number;
  total_overrides: number;
  override_rate: number;
  by_reviewer: Record<string, ReviewerStats>;
  action_distribution: Record<string, number>;
}

export interface ReviewerStats {
  total_actions: number;
  agrees: number;
  overrides: number;
  escalations: number;
  override_rate: number;
}

// Bias Detection
export interface BiasBreakdown {
  decisions_tested: number;
  decisions_with_bias: number;
  bias_detection_rate: number;
  bias_counts: Record<string, number>;
  bias_by_decision_type: Record<string, Record<string, number>>;
}

// Alert Types
export interface Alert {
  alert_type: string;
  title: string;
  details: Record<string, unknown>;
  severity: "info" | "warning" | "error" | "critical";
  timestamp: string;
}

// Fairness Result
export interface FairnessResult {
  result_id: string;
  fairness_score: number;
  biases_detected: string[];
  details: Record<string, unknown>;
  timestamp: string;
}

// Dashboard State
export interface DashboardState {
  connected: boolean;
  metrics: MetricsSummary | null;
  recentDecisions: Decision[];
  alerts: Alert[];
  fairnessResults: FairnessResult[];
  timeSeries: TimeSeriesPoint[];
  reviewerSummary: ReviewerSummary | null;
  biasBreakdown: BiasBreakdown | null;
}

// Health Status
export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;
  version: string;
  environment: string;
  uptime_seconds: number;
  components: Record<string, ComponentHealth>;
  system_metrics: SystemMetrics;
}

export interface ComponentHealth {
  status: "healthy" | "degraded" | "unhealthy" | "unknown";
  message: string;
  details: Record<string, unknown>;
}

export interface SystemMetrics {
  memory: {
    total_mb: number;
    available_mb: number;
    percent_used: number;
  };
  disk: {
    total_gb: number;
    free_gb: number;
    percent_used: number;
  };
  cpu: {
    percent: number;
    count: number;
  };
  process: {
    pid: number;
    memory_mb: number;
  };
}

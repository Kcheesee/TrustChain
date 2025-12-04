/**
 * Main Dashboard Component
 *
 * Real-time TrustChain decision monitoring dashboard.
 *
 * Built with care by Kareem & Claude
 */

import React, { useState, useCallback } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { MetricsCard } from "./MetricsCard";
import { DecisionFeed } from "./DecisionFeed";
import { ConnectionStatus } from "./ConnectionStatus";
import { AlertsPanel } from "./AlertsPanel";
import type { Decision, Alert, MetricsSummary, FairnessResult } from "../types";

const MAX_DECISIONS = 50;
const MAX_ALERTS = 20;

export function Dashboard() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [fairnessResults, setFairnessResults] = useState<FairnessResult[]>([]);

  const handleDecision = useCallback((decision: Decision) => {
    setDecisions((prev) => [decision, ...prev].slice(0, MAX_DECISIONS));
  }, []);

  const handleAlert = useCallback((alert: Alert) => {
    setAlerts((prev) => [alert, ...prev].slice(0, MAX_ALERTS));
  }, []);

  const handleMetrics = useCallback((newMetrics: MetricsSummary) => {
    setMetrics(newMetrics);
  }, []);

  const handleFairness = useCallback((result: FairnessResult) => {
    setFairnessResults((prev) => [result, ...prev].slice(0, 20));
  }, []);

  const dismissAlert = useCallback((index: number) => {
    setAlerts((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const { connected, connecting, error, reconnectAttempt, reconnect } = useWebSocket({
    onDecision: handleDecision,
    onAlert: handleAlert,
    onMetrics: handleMetrics,
    onFairness: handleFairness,
  });

  // Calculate derived metrics
  const approvalRate = metrics?.approval_rate ?? 0;
  const reviewRate = metrics?.review_rate ?? 0;
  const avgConfidence = metrics?.avg_confidence ?? 0;
  const biasRate = metrics?.bias_rate ?? 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                TrustChain Dashboard
              </h1>
              <p className="text-sm text-gray-500">
                Real-time AI decision monitoring
              </p>
            </div>
            <ConnectionStatus
              connected={connected}
              connecting={connecting}
              error={error}
              reconnectAttempt={reconnectAttempt}
              onReconnect={reconnect}
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
          <MetricsCard
            title="Total Decisions"
            value={metrics?.total_decisions ?? decisions.length}
            subtitle="In time window"
            color="blue"
          />
          <MetricsCard
            title="Approval Rate"
            value={`${(approvalRate * 100).toFixed(1)}%`}
            subtitle={`${metrics?.decisions_approved ?? 0} approved`}
            color="green"
            trend={approvalRate > 0.7 ? "up" : approvalRate < 0.3 ? "down" : "neutral"}
          />
          <MetricsCard
            title="Review Rate"
            value={`${(reviewRate * 100).toFixed(1)}%`}
            subtitle={`${metrics?.decisions_needs_review ?? 0} pending`}
            color="yellow"
          />
          <MetricsCard
            title="Avg Confidence"
            value={`${(avgConfidence * 100).toFixed(1)}%`}
            subtitle="Model confidence"
            color="purple"
          />
        </div>

        {/* Fairness Metrics */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-6">
          <MetricsCard
            title="Bias Detection Rate"
            value={`${(biasRate * 100).toFixed(1)}%`}
            subtitle={`${metrics?.decisions_with_bias ?? 0} flagged`}
            color={biasRate > 0.1 ? "red" : "green"}
          />
          <MetricsCard
            title="Fairness Score"
            value={`${((metrics?.avg_fairness_score ?? 0) * 100).toFixed(1)}%`}
            subtitle="Average counterfactual fairness"
            color={metrics?.avg_fairness_score && metrics.avg_fairness_score > 0.8 ? "green" : "yellow"}
          />
          <MetricsCard
            title="Decisions/min"
            value={(metrics?.decisions_per_minute ?? 0).toFixed(1)}
            subtitle="Throughput"
            color="blue"
          />
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Live Decisions */}
          <DecisionFeed decisions={decisions} maxItems={10} />

          {/* Alerts Panel */}
          <AlertsPanel alerts={alerts} maxItems={5} onDismiss={dismissAlert} />
        </div>

        {/* Recent Fairness Results */}
        {fairnessResults.length > 0 && (
          <div className="mt-6 rounded-lg border border-gray-200 bg-white">
            <div className="border-b border-gray-200 px-4 py-3">
              <h3 className="text-sm font-semibold text-gray-800">
                Recent Fairness Tests
              </h3>
            </div>
            <div className="divide-y divide-gray-100">
              {fairnessResults.slice(0, 5).map((result) => (
                <div key={result.result_id} className="px-4 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {result.result_id}
                    </p>
                    <p className="text-xs text-gray-500">
                      {result.biases_detected.length > 0
                        ? `Biases: ${result.biases_detected.join(", ")}`
                        : "No biases detected"}
                    </p>
                  </div>
                  <div
                    className={`text-lg font-semibold ${
                      result.fairness_score > 0.8
                        ? "text-green-600"
                        : result.fairness_score > 0.5
                        ? "text-yellow-600"
                        : "text-red-600"
                    }`}
                  >
                    {(result.fairness_score * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs text-gray-500">
            TrustChain Dashboard • Built with care by Kareem & Claude
          </p>
        </div>
      </footer>
    </div>
  );
}

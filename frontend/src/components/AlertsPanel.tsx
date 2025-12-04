/**
 * Alerts Panel Component
 *
 * Displays system alerts and bias detections.
 *
 * Built with care by Kareem & Claude
 */

import React from "react";
import type { Alert } from "../types";

interface AlertsPanelProps {
  alerts: Alert[];
  maxItems?: number;
  onDismiss?: (index: number) => void;
}

const severityStyles = {
  info: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    text: "text-blue-800",
    icon: "ℹ️",
  },
  warning: {
    bg: "bg-yellow-50",
    border: "border-yellow-200",
    text: "text-yellow-800",
    icon: "⚠️",
  },
  error: {
    bg: "bg-red-50",
    border: "border-red-200",
    text: "text-red-800",
    icon: "❌",
  },
  critical: {
    bg: "bg-red-100",
    border: "border-red-300",
    text: "text-red-900",
    icon: "🚨",
  },
};

export function AlertsPanel({ alerts, maxItems = 5, onDismiss }: AlertsPanelProps) {
  const displayedAlerts = alerts.slice(0, maxItems);

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-800">Alerts</h3>
        <p className="text-xs text-gray-500">System notifications and bias alerts</p>
      </div>

      <div className="divide-y divide-gray-100">
        {displayedAlerts.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">
            No alerts. System is operating normally.
          </div>
        ) : (
          displayedAlerts.map((alert, index) => {
            const style = severityStyles[alert.severity];
            return (
              <div
                key={`${alert.timestamp}-${index}`}
                className={`flex items-start gap-3 px-4 py-3 ${style.bg}`}
              >
                <span className="text-lg">{style.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${style.text}`}>
                    {alert.title}
                  </p>
                  <p className="text-xs text-gray-600 mt-1">
                    {alert.alert_type} • {new Date(alert.timestamp).toLocaleTimeString()}
                  </p>
                </div>
                {onDismiss && (
                  <button
                    onClick={() => onDismiss(index)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ×
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

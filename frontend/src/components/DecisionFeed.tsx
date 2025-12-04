/**
 * Decision Feed Component
 *
 * Real-time feed of incoming decisions.
 *
 * Built with care by Kareem & Claude
 */

import React from "react";
import type { Decision } from "../types";

interface DecisionFeedProps {
  decisions: Decision[];
  maxItems?: number;
}

const decisionColors = {
  approved: "bg-green-100 text-green-800 border-green-200",
  denied: "bg-red-100 text-red-800 border-red-200",
  needs_review: "bg-yellow-100 text-yellow-800 border-yellow-200",
};

const decisionLabels = {
  approved: "Approved",
  denied: "Denied",
  needs_review: "Review",
};

export function DecisionFeed({ decisions, maxItems = 10 }: DecisionFeedProps) {
  const displayedDecisions = decisions.slice(0, maxItems);

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-800">Live Decisions</h3>
        <p className="text-xs text-gray-500">Real-time decision stream</p>
      </div>

      <div className="divide-y divide-gray-100">
        {displayedDecisions.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">
            No decisions yet. Waiting for data...
          </div>
        ) : (
          displayedDecisions.map((decision) => (
            <div
              key={decision.result_id}
              className="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {decision.case_id}
                </p>
                <p className="text-xs text-gray-500">
                  {decision.decision_type} • {Math.round(decision.confidence * 100)}% confidence
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
                    decisionColors[decision.final_decision]
                  }`}
                >
                  {decisionLabels[decision.final_decision]}
                </span>

                {decision.requires_review && (
                  <span className="inline-flex items-center rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
                    Review
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {decisions.length > maxItems && (
        <div className="border-t border-gray-200 px-4 py-2 text-center">
          <button className="text-xs text-blue-600 hover:text-blue-800">
            View all {decisions.length} decisions
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Metrics Card Component
 *
 * Displays a single metric with icon and trend indicator.
 *
 * Built with care by Kareem & Claude
 */

import React from "react";

interface MetricsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  color?: "blue" | "green" | "yellow" | "red" | "purple";
}

const colorClasses = {
  blue: "bg-blue-50 border-blue-200 text-blue-600",
  green: "bg-green-50 border-green-200 text-green-600",
  yellow: "bg-yellow-50 border-yellow-200 text-yellow-600",
  red: "bg-red-50 border-red-200 text-red-600",
  purple: "bg-purple-50 border-purple-200 text-purple-600",
};

const trendColors = {
  up: "text-green-600",
  down: "text-red-600",
  neutral: "text-gray-500",
};

export function MetricsCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  color = "blue",
}: MetricsCardProps) {
  return (
    <div className={`rounded-lg border p-4 ${colorClasses[color]}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="mt-1 text-2xl font-semibold">{value}</p>
          {subtitle && (
            <p className="mt-1 text-xs text-gray-500">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="flex-shrink-0 rounded-full bg-white/50 p-2">
            {icon}
          </div>
        )}
      </div>
      {trend && trendValue && (
        <div className={`mt-2 text-xs ${trendColors[trend]}`}>
          {trend === "up" && "↑ "}
          {trend === "down" && "↓ "}
          {trendValue}
        </div>
      )}
    </div>
  );
}

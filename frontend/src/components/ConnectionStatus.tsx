/**
 * Connection Status Component
 *
 * Shows WebSocket connection status.
 *
 * Built with care by Kareem & Claude
 */

import React from "react";

interface ConnectionStatusProps {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  reconnectAttempt: number;
  onReconnect?: () => void;
}

export function ConnectionStatus({
  connected,
  connecting,
  error,
  reconnectAttempt,
  onReconnect,
}: ConnectionStatusProps) {
  let statusColor = "bg-gray-400";
  let statusText = "Disconnected";

  if (connected) {
    statusColor = "bg-green-500";
    statusText = "Connected";
  } else if (connecting) {
    statusColor = "bg-yellow-500 animate-pulse";
    statusText = "Connecting...";
  } else if (error) {
    statusColor = "bg-red-500";
    statusText = "Error";
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-2">
      <div className="flex items-center gap-2">
        <div className={`h-2.5 w-2.5 rounded-full ${statusColor}`} />
        <span className="text-sm font-medium text-gray-700">{statusText}</span>
      </div>

      {error && (
        <span className="text-xs text-red-600">{error}</span>
      )}

      {reconnectAttempt > 0 && !connected && (
        <span className="text-xs text-gray-500">
          Attempt {reconnectAttempt}
        </span>
      )}

      {!connected && !connecting && onReconnect && (
        <button
          onClick={onReconnect}
          className="ml-2 rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700"
        >
          Reconnect
        </button>
      )}
    </div>
  );
}

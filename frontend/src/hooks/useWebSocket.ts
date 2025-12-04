/**
 * TrustChain WebSocket Hook
 *
 * Custom React hook for real-time WebSocket connection to TrustChain API.
 *
 * Built with care by Kareem & Claude
 */

import { useState, useEffect, useCallback, useRef } from "react";
import type {
  WebSocketMessage,
  Decision,
  Alert,
  FairnessResult,
  MetricsSummary,
} from "../types";

interface UseWebSocketOptions {
  url?: string;
  channels?: string[];
  onDecision?: (decision: Decision) => void;
  onAlert?: (alert: Alert) => void;
  onFairness?: (result: FairnessResult) => void;
  onMetrics?: (metrics: MetricsSummary) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UseWebSocketReturn {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  reconnectAttempt: number;
  lastMessage: WebSocketMessage | null;
  send: (message: Record<string, unknown>) => void;
  disconnect: () => void;
  reconnect: () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = `ws://${window.location.hostname}:8000/ws/stream`,
    channels = ["decisions", "alerts", "metrics", "fairness"],
    onDecision,
    onAlert,
    onFairness,
    onMetrics,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
  } = options;

  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnecting(true);
    setError(null);

    // Build URL with channels
    const params = new URLSearchParams();
    channels.forEach((ch) => params.append("channels", ch));
    const wsUrl = `${url}?${params.toString()}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setConnecting(false);
      setReconnectAttempt(0);
      setError(null);
      console.log("[TrustChain WS] Connected");
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);

        // Route message to appropriate handler
        switch (message.type) {
          case "decision":
            if (onDecision && message.data) {
              onDecision(message.data as unknown as Decision);
            }
            break;
          case "alert":
            if (onAlert && message.data) {
              onAlert(message.data as unknown as Alert);
            }
            break;
          case "fairness_result":
            if (onFairness && message.data) {
              onFairness(message.data as unknown as FairnessResult);
            }
            break;
          case "metrics":
            if (onMetrics && message.data) {
              onMetrics(message.data as unknown as MetricsSummary);
            }
            break;
          case "connected":
            console.log("[TrustChain WS] Welcome message received");
            break;
        }
      } catch (err) {
        console.error("[TrustChain WS] Failed to parse message:", err);
      }
    };

    ws.onerror = (event) => {
      console.error("[TrustChain WS] Error:", event);
      setError("WebSocket connection error");
    };

    ws.onclose = (event) => {
      setConnected(false);
      setConnecting(false);
      console.log("[TrustChain WS] Disconnected:", event.code, event.reason);

      // Auto-reconnect if not intentional close
      if (event.code !== 1000 && reconnectAttempt < maxReconnectAttempts) {
        setReconnectAttempt((prev) => prev + 1);
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log(`[TrustChain WS] Reconnecting (attempt ${reconnectAttempt + 1})...`);
          connect();
        }, reconnectInterval);
      }
    };
  }, [url, channels, onDecision, onAlert, onFairness, onMetrics, reconnectAttempt, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close(1000, "User disconnect");
      wsRef.current = null;
    }
    setConnected(false);
    setConnecting(false);
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    setReconnectAttempt(0);
    connect();
  }, [connect, disconnect]);

  const send = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn("[TrustChain WS] Cannot send - not connected");
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, []);

  return {
    connected,
    connecting,
    error,
    reconnectAttempt,
    lastMessage,
    send,
    disconnect,
    reconnect,
  };
}

"""
TrustChain WebSocket Manager

Real-time streaming for decisions, metrics, and alerts.

Usage:
    # In FastAPI app
    from services.websocket_manager import manager

    @app.websocket("/ws/decisions")
    async def websocket_decisions(websocket: WebSocket):
        await manager.connect(websocket, "decisions")
        try:
            while True:
                data = await websocket.receive_text()
                # Handle incoming messages
        except WebSocketDisconnect:
            manager.disconnect(websocket, "decisions")

    # Broadcast from anywhere
    await manager.broadcast_decision(result)

Built with care by Kareem & Claude
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """WebSocket channel types."""
    DECISIONS = "decisions"           # Live decision stream
    METRICS = "metrics"               # Real-time metrics updates
    ALERTS = "alerts"                 # Bias alerts and system notifications
    REVIEWER_ACTIVITY = "reviewers"   # Reviewer actions
    FAIRNESS = "fairness"             # Counterfactual fairness results
    ALL = "all"                       # Subscribe to everything


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection with metadata."""
    websocket: WebSocket
    channels: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.now)
    client_id: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)  # e.g., {"decision_type": "hiring"}


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasting.

    Features:
    - Multi-channel subscriptions (decisions, metrics, alerts)
    - Filtered broadcasts (by decision type, reviewer, etc.)
    - Connection tracking and statistics
    - Graceful disconnect handling
    """

    def __init__(self):
        # Channel -> Set of WebSocket connections
        self._channels: Dict[str, Set[WebSocket]] = {
            channel.value: set() for channel in ChannelType
        }
        # WebSocket -> Connection metadata
        self._connections: Dict[WebSocket, WebSocketConnection] = {}
        # Stats
        self._total_messages_sent = 0
        self._total_connections = 0

    async def connect(
        self,
        websocket: WebSocket,
        channels: List[str] = None,
        client_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> WebSocketConnection:
        """
        Accept a WebSocket connection and subscribe to channels.

        Args:
            websocket: The WebSocket connection
            channels: List of channels to subscribe to (default: ["decisions"])
            client_id: Optional client identifier
            filters: Optional filters for messages (e.g., {"decision_type": "hiring"})

        Returns:
            WebSocketConnection with metadata
        """
        await websocket.accept()

        channels = channels or [ChannelType.DECISIONS.value]

        # Create connection metadata
        connection = WebSocketConnection(
            websocket=websocket,
            channels=set(channels),
            client_id=client_id,
            filters=filters or {}
        )

        # Register in channels
        for channel in channels:
            if channel in self._channels:
                self._channels[channel].add(websocket)
            elif channel == ChannelType.ALL.value:
                # Subscribe to all channels
                for ch in self._channels.values():
                    ch.add(websocket)

        self._connections[websocket] = connection
        self._total_connections += 1

        logger.info(
            f"WebSocket connected: client={client_id or 'anonymous'}, "
            f"channels={channels}, total_active={len(self._connections)}"
        )

        # Send welcome message
        await self._send_to_websocket(websocket, {
            "type": "connected",
            "channels": list(connection.channels),
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to TrustChain real-time stream"
        })

        return connection

    def disconnect(self, websocket: WebSocket, reason: str = "client_disconnect"):
        """
        Remove a WebSocket connection from all channels.

        Args:
            websocket: The WebSocket to disconnect
            reason: Reason for disconnect (for logging)
        """
        if websocket not in self._connections:
            return

        connection = self._connections[websocket]

        # Remove from all channels
        for channel_set in self._channels.values():
            channel_set.discard(websocket)

        del self._connections[websocket]

        logger.info(
            f"WebSocket disconnected: client={connection.client_id or 'anonymous'}, "
            f"reason={reason}, total_active={len(self._connections)}"
        )

    async def broadcast_decision(self, result: Any) -> int:
        """
        Broadcast a decision result to the decisions channel.

        Args:
            result: AccountabilityResult or dict

        Returns:
            Number of clients that received the message
        """
        # Convert to dict if needed
        if hasattr(result, 'to_dict'):
            data = result.to_dict()
        else:
            data = result

        message = {
            "type": "decision",
            "data": {
                "result_id": data.get("result_id"),
                "case_id": data.get("case_id"),
                "decision_type": data.get("decision_type"),
                "final_decision": data.get("final_decision"),
                "confidence": data.get("overall_confidence"),
                "requires_review": data.get("requires_human_review"),
                "review_triggers": data.get("review_triggers", []),
                "timestamp": data.get("timestamp") or datetime.now().isoformat(),
            },
            "timestamp": datetime.now().isoformat()
        }

        return await self._broadcast(ChannelType.DECISIONS.value, message, data)

    async def broadcast_metrics(self, metrics: Dict[str, Any]) -> int:
        """
        Broadcast metrics update to the metrics channel.

        Args:
            metrics: Dictionary of metrics

        Returns:
            Number of clients that received the message
        """
        message = {
            "type": "metrics",
            "data": metrics,
            "timestamp": datetime.now().isoformat()
        }

        return await self._broadcast(ChannelType.METRICS.value, message)

    async def broadcast_alert(
        self,
        alert_type: str,
        title: str,
        details: Dict[str, Any],
        severity: str = "warning"
    ) -> int:
        """
        Broadcast an alert (bias detected, system issue, etc.)

        Args:
            alert_type: Type of alert (bias_detected, system_error, etc.)
            title: Alert title
            details: Alert details
            severity: info, warning, error, critical

        Returns:
            Number of clients that received the message
        """
        message = {
            "type": "alert",
            "data": {
                "alert_type": alert_type,
                "title": title,
                "details": details,
                "severity": severity,
            },
            "timestamp": datetime.now().isoformat()
        }

        return await self._broadcast(ChannelType.ALERTS.value, message)

    async def broadcast_reviewer_activity(
        self,
        reviewer_id: str,
        action: str,
        result_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Broadcast reviewer activity.

        Args:
            reviewer_id: ID of the reviewer
            action: Action taken (agree, override, escalate)
            result_id: Related result ID
            details: Additional details

        Returns:
            Number of clients that received the message
        """
        message = {
            "type": "reviewer_activity",
            "data": {
                "reviewer_id": reviewer_id,
                "action": action,
                "result_id": result_id,
                "details": details or {},
            },
            "timestamp": datetime.now().isoformat()
        }

        return await self._broadcast(ChannelType.REVIEWER_ACTIVITY.value, message)

    async def broadcast_fairness_result(
        self,
        result_id: str,
        fairness_score: float,
        biases_detected: List[str],
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Broadcast counterfactual fairness test result.

        Args:
            result_id: Result ID
            fairness_score: 0.0-1.0 fairness score
            biases_detected: List of detected biases
            details: Full counterfactual analysis

        Returns:
            Number of clients that received the message
        """
        message = {
            "type": "fairness_result",
            "data": {
                "result_id": result_id,
                "fairness_score": fairness_score,
                "biases_detected": biases_detected,
                "details": details or {},
            },
            "timestamp": datetime.now().isoformat()
        }

        return await self._broadcast(ChannelType.FAIRNESS.value, message)

    async def _broadcast(
        self,
        channel: str,
        message: Dict[str, Any],
        filter_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Internal broadcast method with filtering support.

        Args:
            channel: Channel to broadcast to
            message: Message to send
            filter_data: Data to use for filtering (e.g., decision_type)

        Returns:
            Number of clients that received the message
        """
        if channel not in self._channels:
            logger.warning(f"Unknown channel: {channel}")
            return 0

        sent_count = 0
        disconnected = []

        for websocket in self._channels[channel]:
            connection = self._connections.get(websocket)

            # Apply filters if present
            if connection and connection.filters and filter_data:
                if not self._matches_filter(filter_data, connection.filters):
                    continue

            try:
                await self._send_to_websocket(websocket, message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to websocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, reason="send_failed")

        self._total_messages_sent += sent_count
        return sent_count

    def _matches_filter(
        self,
        data: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> bool:
        """Check if data matches the connection's filters."""
        for key, value in filters.items():
            if key in data and data[key] != value:
                return False
        return True

    async def _send_to_websocket(
        self,
        websocket: WebSocket,
        message: Dict[str, Any]
    ):
        """Send a message to a specific websocket."""
        await websocket.send_json(message)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        channel_counts = {
            channel: len(connections)
            for channel, connections in self._channels.items()
        }

        return {
            "active_connections": len(self._connections),
            "total_connections_ever": self._total_connections,
            "total_messages_sent": self._total_messages_sent,
            "channels": channel_counts,
            "timestamp": datetime.now().isoformat()
        }

    def get_connection_info(self, websocket: WebSocket) -> Optional[Dict[str, Any]]:
        """Get info about a specific connection."""
        connection = self._connections.get(websocket)
        if not connection:
            return None

        return {
            "client_id": connection.client_id,
            "channels": list(connection.channels),
            "connected_at": connection.connected_at.isoformat(),
            "filters": connection.filters
        }


# Global manager instance
manager = ConnectionManager()

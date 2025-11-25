"""
Feedback Storage Module for TrustChain.

Provides persistent storage for human feedback with multiple backends:
- InMemoryFeedbackStore: For testing
- SQLiteFeedbackStore: For local development
- PostgresFeedbackStore: For production

Built with care by Kareem & Claude
"""

import logging
import sqlite3
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta
from pathlib import Path

from .capture import HumanFeedback, FeedbackStats, ReviewerAction, OverrideReason

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Global store instance
_feedback_store: Optional["FeedbackStore"] = None


def get_feedback_store() -> "FeedbackStore":
    """Get the global feedback store instance."""
    global _feedback_store
    if _feedback_store is None:
        # Default to SQLite for persistence
        _feedback_store = SQLiteFeedbackStore()
    return _feedback_store


def set_feedback_store(store: "FeedbackStore") -> None:
    """Set the global feedback store instance."""
    global _feedback_store
    _feedback_store = store


class FeedbackStore(ABC):
    """Abstract base for feedback storage."""

    @abstractmethod
    async def save_feedback(self, feedback: HumanFeedback) -> str:
        """Save feedback, return feedback ID."""
        pass

    @abstractmethod
    async def get_feedback(self, feedback_id: str) -> Optional[HumanFeedback]:
        """Get feedback by ID."""
        pass

    @abstractmethod
    async def get_feedback_for_result(self, result_id: str) -> Optional[HumanFeedback]:
        """Get feedback for a specific TrustChain result."""
        pass

    @abstractmethod
    async def get_feedback_batch(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        action: Optional[ReviewerAction] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[HumanFeedback]:
        """Query feedback with filters."""
        pass

    @abstractmethod
    async def compute_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> FeedbackStats:
        """Compute aggregate statistics."""
        pass

    @abstractmethod
    async def update_outcome(
        self,
        result_id: str,
        final_outcome: str,
        outcome_timestamp: datetime,
        notes: str = ""
    ) -> bool:
        """Update with final outcome (for tracking long-term accuracy)."""
        pass

    @abstractmethod
    async def count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> int:
        """Count feedback entries matching filters."""
        pass


class InMemoryFeedbackStore(FeedbackStore):
    """
    In-memory store for testing.

    Fast but not persistent - data lost on restart.
    """

    def __init__(self):
        self._feedback: Dict[str, HumanFeedback] = {}
        self._result_index: Dict[str, str] = {}  # result_id -> feedback_id
        logger.info("InMemoryFeedbackStore initialized")

    async def save_feedback(self, feedback: HumanFeedback) -> str:
        """Save feedback to memory."""
        self._feedback[feedback.feedback_id] = feedback
        self._result_index[feedback.result_id] = feedback.feedback_id
        logger.debug(f"Saved feedback {feedback.feedback_id} for result {feedback.result_id}")
        return feedback.feedback_id

    async def get_feedback(self, feedback_id: str) -> Optional[HumanFeedback]:
        """Get feedback by ID."""
        return self._feedback.get(feedback_id)

    async def get_feedback_for_result(self, result_id: str) -> Optional[HumanFeedback]:
        """Get feedback for a TrustChain result."""
        feedback_id = self._result_index.get(result_id)
        if feedback_id:
            return self._feedback.get(feedback_id)
        return None

    async def get_feedback_batch(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        action: Optional[ReviewerAction] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[HumanFeedback]:
        """Query feedback with filters."""
        results = []

        for feedback in self._feedback.values():
            # Apply filters
            if start_date and feedback.timestamp < start_date:
                continue
            if end_date and feedback.timestamp > end_date:
                continue
            if reviewer_id and feedback.reviewer_id != reviewer_id:
                continue
            if action and feedback.action != action:
                continue
            # Note: decision_type filtering would need result lookup

            results.append(feedback)

        # Sort by timestamp descending
        results.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply pagination
        return results[offset:offset + limit]

    async def compute_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> FeedbackStats:
        """Compute aggregate statistics."""
        feedback_list = await self.get_feedback_batch(
            start_date=start_date,
            end_date=end_date,
            decision_type=decision_type,
            limit=100000
        )

        stats = FeedbackStats(
            period_start=start_date,
            period_end=end_date or datetime.now()
        )

        if not feedback_list:
            return stats

        stats.total_reviewed = len(feedback_list)

        # Count agreements and overrides
        agreements = sum(1 for f in feedback_list if f.action.is_agreement)
        overrides = sum(1 for f in feedback_list if f.action.is_override)

        stats.total_overrides = overrides
        stats.agreement_rate = agreements / len(feedback_list) if feedback_list else 0
        stats.override_rate = overrides / len(feedback_list) if feedback_list else 0

        # Count analyzer false positives/negatives
        for feedback in feedback_list:
            for analyzer in feedback.incorrect_flags:
                stats.analyzer_false_positives[analyzer] = (
                    stats.analyzer_false_positives.get(analyzer, 0) + 1
                )
            for analyzer in feedback.missed_flags:
                stats.analyzer_false_negatives[analyzer] = (
                    stats.analyzer_false_negatives.get(analyzer, 0) + 1
                )

        # Count override reasons
        for feedback in feedback_list:
            if feedback.override_reason:
                reason = feedback.override_reason.value
                stats.override_reasons[reason] = stats.override_reasons.get(reason, 0) + 1

        # Calculate false positive rate from incorrect_flags
        total_flags = sum(stats.analyzer_false_positives.values())
        if stats.total_reviewed > 0:
            stats.false_positive_rate = total_flags / stats.total_reviewed

        # Calculate false negative rate from missed_flags
        total_missed = sum(stats.analyzer_false_negatives.values())
        if stats.total_reviewed > 0:
            stats.false_negative_rate = total_missed / stats.total_reviewed

        # Average review time
        review_times = [f.time_spent_seconds for f in feedback_list if f.time_spent_seconds]
        if review_times:
            stats.avg_review_time_seconds = sum(review_times) / len(review_times)

        # Outcome tracking
        outcomes = [f for f in feedback_list if f.outcome_tracked]
        stats.outcomes_tracked = len(outcomes)

        return stats

    async def update_outcome(
        self,
        result_id: str,
        final_outcome: str,
        outcome_timestamp: datetime,
        notes: str = ""
    ) -> bool:
        """Update feedback with final outcome."""
        feedback = await self.get_feedback_for_result(result_id)
        if feedback:
            feedback.outcome_tracked = True
            feedback.final_outcome = final_outcome
            feedback.outcome_timestamp = outcome_timestamp
            feedback.outcome_notes = notes
            return True
        return False

    async def count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> int:
        """Count matching feedback entries."""
        batch = await self.get_feedback_batch(
            start_date=start_date,
            end_date=end_date,
            decision_type=decision_type,
            limit=100000
        )
        return len(batch)

    def clear(self):
        """Clear all data (for testing)."""
        self._feedback.clear()
        self._result_index.clear()


class SQLiteFeedbackStore(FeedbackStore):
    """
    SQLite implementation for local development.

    Persistent storage with full query support.
    """

    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
        self._init_db()
        logger.info(f"SQLiteFeedbackStore initialized at {db_path}")

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                result_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                reviewer_role TEXT,
                action TEXT NOT NULL,
                override_reason TEXT,
                reasoning TEXT,
                additional_context TEXT,
                incorrect_flags TEXT,
                missed_flags TEXT,
                reviewer_confidence REAL,
                timestamp TEXT NOT NULL,
                time_spent_seconds INTEGER,
                outcome_tracked INTEGER DEFAULT 0,
                final_outcome TEXT,
                outcome_timestamp TEXT,
                outcome_notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_result_id ON feedback(result_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON feedback(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviewer_id ON feedback(reviewer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_action ON feedback(action)")

        conn.commit()
        conn.close()

    def _feedback_to_row(self, feedback: HumanFeedback) -> tuple:
        """Convert HumanFeedback to database row."""
        return (
            feedback.feedback_id,
            feedback.result_id,
            feedback.case_id,
            feedback.reviewer_id,
            feedback.reviewer_role,
            feedback.action.value,
            feedback.override_reason.value if feedback.override_reason else None,
            feedback.reasoning,
            feedback.additional_context,
            json.dumps(feedback.incorrect_flags),
            json.dumps(feedback.missed_flags),
            feedback.reviewer_confidence,
            feedback.timestamp.isoformat(),
            feedback.time_spent_seconds,
            1 if feedback.outcome_tracked else 0,
            feedback.final_outcome,
            feedback.outcome_timestamp.isoformat() if feedback.outcome_timestamp else None,
            feedback.outcome_notes,
        )

    def _row_to_feedback(self, row: tuple) -> HumanFeedback:
        """Convert database row to HumanFeedback."""
        return HumanFeedback(
            feedback_id=row[0],
            result_id=row[1],
            case_id=row[2],
            reviewer_id=row[3],
            reviewer_role=row[4] or "reviewer",
            action=ReviewerAction(row[5]),
            override_reason=OverrideReason(row[6]) if row[6] else None,
            reasoning=row[7] or "",
            additional_context=row[8] or "",
            incorrect_flags=json.loads(row[9]) if row[9] else [],
            missed_flags=json.loads(row[10]) if row[10] else [],
            reviewer_confidence=row[11] or 1.0,
            timestamp=datetime.fromisoformat(row[12]),
            time_spent_seconds=row[13],
            outcome_tracked=bool(row[14]),
            final_outcome=row[15],
            outcome_timestamp=datetime.fromisoformat(row[16]) if row[16] else None,
            outcome_notes=row[17] or "",
        )

    async def save_feedback(self, feedback: HumanFeedback) -> str:
        """Save feedback to SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO feedback (
                feedback_id, result_id, case_id, reviewer_id, reviewer_role,
                action, override_reason, reasoning, additional_context,
                incorrect_flags, missed_flags, reviewer_confidence,
                timestamp, time_spent_seconds, outcome_tracked,
                final_outcome, outcome_timestamp, outcome_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, self._feedback_to_row(feedback))

        conn.commit()
        conn.close()

        logger.debug(f"Saved feedback {feedback.feedback_id}")
        return feedback.feedback_id

    async def get_feedback(self, feedback_id: str) -> Optional[HumanFeedback]:
        """Get feedback by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM feedback WHERE feedback_id = ?", (feedback_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_feedback(row)
        return None

    async def get_feedback_for_result(self, result_id: str) -> Optional[HumanFeedback]:
        """Get feedback for a TrustChain result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM feedback WHERE result_id = ?", (result_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_feedback(row)
        return None

    async def get_feedback_batch(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        action: Optional[ReviewerAction] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[HumanFeedback]:
        """Query feedback with filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM feedback WHERE 1=1"
        params = []

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        if reviewer_id:
            query += " AND reviewer_id = ?"
            params.append(reviewer_id)

        if action:
            query += " AND action = ?"
            params.append(action.value)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_feedback(row) for row in rows]

    async def compute_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> FeedbackStats:
        """Compute aggregate statistics using SQL."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build WHERE clause
        where = "WHERE 1=1"
        params = []

        if start_date:
            where += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            where += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        stats = FeedbackStats(
            period_start=start_date,
            period_end=end_date or datetime.now()
        )

        # Total count
        cursor.execute(f"SELECT COUNT(*) FROM feedback {where}", params)
        stats.total_reviewed = cursor.fetchone()[0]

        if stats.total_reviewed == 0:
            conn.close()
            return stats

        # Agreement actions
        agreement_actions = [
            ReviewerAction.AGREE_APPROVE.value,
            ReviewerAction.AGREE_DENY.value,
            ReviewerAction.AGREE_FLAG.value,
        ]
        placeholders = ",".join("?" * len(agreement_actions))
        cursor.execute(
            f"SELECT COUNT(*) FROM feedback {where} AND action IN ({placeholders})",
            params + agreement_actions
        )
        agreements = cursor.fetchone()[0]

        # Override actions
        override_actions = [
            ReviewerAction.OVERRIDE_TO_APPROVE.value,
            ReviewerAction.OVERRIDE_TO_DENY.value,
        ]
        placeholders = ",".join("?" * len(override_actions))
        cursor.execute(
            f"SELECT COUNT(*) FROM feedback {where} AND action IN ({placeholders})",
            params + override_actions
        )
        overrides = cursor.fetchone()[0]

        stats.total_overrides = overrides
        stats.agreement_rate = agreements / stats.total_reviewed
        stats.override_rate = overrides / stats.total_reviewed

        # Override reasons
        cursor.execute(
            f"SELECT override_reason, COUNT(*) FROM feedback {where} AND override_reason IS NOT NULL GROUP BY override_reason",
            params
        )
        for row in cursor.fetchall():
            stats.override_reasons[row[0]] = row[1]

        # Average review time
        cursor.execute(
            f"SELECT AVG(time_spent_seconds) FROM feedback {where} AND time_spent_seconds IS NOT NULL",
            params
        )
        result = cursor.fetchone()[0]
        if result:
            stats.avg_review_time_seconds = result

        # Outcome tracking
        cursor.execute(
            f"SELECT COUNT(*) FROM feedback {where} AND outcome_tracked = 1",
            params
        )
        stats.outcomes_tracked = cursor.fetchone()[0]

        # Get all feedback for analyzer stats (need to parse JSON)
        feedback_list = await self.get_feedback_batch(
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )

        for feedback in feedback_list:
            for analyzer in feedback.incorrect_flags:
                stats.analyzer_false_positives[analyzer] = (
                    stats.analyzer_false_positives.get(analyzer, 0) + 1
                )
            for analyzer in feedback.missed_flags:
                stats.analyzer_false_negatives[analyzer] = (
                    stats.analyzer_false_negatives.get(analyzer, 0) + 1
                )

        total_flags = sum(stats.analyzer_false_positives.values())
        stats.false_positive_rate = total_flags / stats.total_reviewed

        total_missed = sum(stats.analyzer_false_negatives.values())
        stats.false_negative_rate = total_missed / stats.total_reviewed

        conn.close()
        return stats

    async def update_outcome(
        self,
        result_id: str,
        final_outcome: str,
        outcome_timestamp: datetime,
        notes: str = ""
    ) -> bool:
        """Update feedback with final outcome."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE feedback
            SET outcome_tracked = 1,
                final_outcome = ?,
                outcome_timestamp = ?,
                outcome_notes = ?
            WHERE result_id = ?
        """, (final_outcome, outcome_timestamp.isoformat(), notes, result_id))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return updated

    async def count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> int:
        """Count matching feedback entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM feedback WHERE 1=1"
        params = []

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()

        return count


class PostgresFeedbackStore(FeedbackStore):
    """
    PostgreSQL implementation for production.

    Uses SQLAlchemy ORM for database operations.
    Thread-safe and supports connection pooling.
    """

    def __init__(self, session_factory):
        """
        Initialize with SQLAlchemy session factory.

        Args:
            session_factory: Callable that returns a new Session
        """
        self._session_factory = session_factory
        logger.info("PostgresFeedbackStore initialized")

    def _get_session(self) -> "Session":
        """Get a new database session."""
        return self._session_factory()

    def _feedback_to_model(self, feedback: HumanFeedback):
        """Convert HumanFeedback dataclass to SQLAlchemy model."""
        # Import here to avoid circular imports
        from database.models import HumanFeedback as HumanFeedbackModel

        return HumanFeedbackModel(
            feedback_id=feedback.feedback_id,
            result_id=feedback.result_id,
            reviewer_id=feedback.reviewer_id,
            action=feedback.action.value,
            original_decision=feedback.original_decision,
            final_decision=feedback.final_decision,
            override_reason=feedback.override_reason.value if feedback.override_reason else None,
            confidence_adjustment=feedback.confidence_adjustment,
            decision_type=getattr(feedback, 'decision_type', None),
            notes=feedback.reasoning,
            created_at=feedback.timestamp,
        )

    def _model_to_feedback(self, model) -> HumanFeedback:
        """Convert SQLAlchemy model to HumanFeedback dataclass."""
        return HumanFeedback(
            feedback_id=model.feedback_id,
            result_id=model.result_id,
            case_id=model.result_id,  # Use result_id as case_id for now
            reviewer_id=model.reviewer_id,
            action=ReviewerAction(model.action),
            override_reason=OverrideReason(model.override_reason) if model.override_reason else None,
            reasoning=model.notes or "",
            timestamp=model.created_at,
            original_decision=model.original_decision,
            final_decision=model.final_decision,
            confidence_adjustment=model.confidence_adjustment,
            outcome_tracked=model.outcome is not None,
            final_outcome=model.outcome,
            outcome_timestamp=model.outcome_recorded_at,
        )

    async def save_feedback(self, feedback: HumanFeedback) -> str:
        """Save feedback to PostgreSQL."""
        session = self._get_session()
        try:
            model = self._feedback_to_model(feedback)
            session.add(model)
            session.commit()
            logger.debug(f"Saved feedback {feedback.feedback_id}")
            return feedback.feedback_id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving feedback: {e}")
            raise
        finally:
            session.close()

    async def get_feedback(self, feedback_id: str) -> Optional[HumanFeedback]:
        """Get feedback by ID."""
        from database.models import HumanFeedback as HumanFeedbackModel

        session = self._get_session()
        try:
            model = session.query(HumanFeedbackModel).filter(
                HumanFeedbackModel.feedback_id == feedback_id
            ).first()

            if model:
                return self._model_to_feedback(model)
            return None
        finally:
            session.close()

    async def get_feedback_for_result(self, result_id: str) -> Optional[HumanFeedback]:
        """Get feedback for a TrustChain result."""
        from database.models import HumanFeedback as HumanFeedbackModel

        session = self._get_session()
        try:
            model = session.query(HumanFeedbackModel).filter(
                HumanFeedbackModel.result_id == result_id
            ).first()

            if model:
                return self._model_to_feedback(model)
            return None
        finally:
            session.close()

    async def get_feedback_batch(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        action: Optional[ReviewerAction] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[HumanFeedback]:
        """Query feedback with filters."""
        from database.models import HumanFeedback as HumanFeedbackModel
        from sqlalchemy import desc

        session = self._get_session()
        try:
            query = session.query(HumanFeedbackModel)

            if start_date:
                query = query.filter(HumanFeedbackModel.created_at >= start_date)
            if end_date:
                query = query.filter(HumanFeedbackModel.created_at <= end_date)
            if decision_type:
                query = query.filter(HumanFeedbackModel.decision_type == decision_type)
            if reviewer_id:
                query = query.filter(HumanFeedbackModel.reviewer_id == reviewer_id)
            if action:
                query = query.filter(HumanFeedbackModel.action == action.value)

            query = query.order_by(desc(HumanFeedbackModel.created_at))
            query = query.limit(limit).offset(offset)

            models = query.all()
            return [self._model_to_feedback(m) for m in models]
        finally:
            session.close()

    async def compute_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> FeedbackStats:
        """Compute aggregate statistics using SQL."""
        from database.models import HumanFeedback as HumanFeedbackModel
        from sqlalchemy import func

        session = self._get_session()
        try:
            stats = FeedbackStats(
                period_start=start_date,
                period_end=end_date or datetime.now()
            )

            # Base query with filters
            query = session.query(HumanFeedbackModel)
            if start_date:
                query = query.filter(HumanFeedbackModel.created_at >= start_date)
            if end_date:
                query = query.filter(HumanFeedbackModel.created_at <= end_date)
            if decision_type:
                query = query.filter(HumanFeedbackModel.decision_type == decision_type)

            # Total count
            stats.total_reviewed = query.count()

            if stats.total_reviewed == 0:
                return stats

            # Agreement count
            agreement_actions = [
                ReviewerAction.AGREE_APPROVE.value,
                ReviewerAction.AGREE_DENY.value,
                ReviewerAction.AGREE_FLAG.value,
            ]
            agreements = query.filter(
                HumanFeedbackModel.action.in_(agreement_actions)
            ).count()

            # Override count
            override_actions = [
                ReviewerAction.OVERRIDE_TO_APPROVE.value,
                ReviewerAction.OVERRIDE_TO_DENY.value,
            ]
            overrides = query.filter(
                HumanFeedbackModel.action.in_(override_actions)
            ).count()

            stats.total_overrides = overrides
            stats.agreement_rate = agreements / stats.total_reviewed
            stats.override_rate = overrides / stats.total_reviewed

            # Override reasons
            reason_counts = session.query(
                HumanFeedbackModel.override_reason,
                func.count(HumanFeedbackModel.id)
            ).filter(
                HumanFeedbackModel.override_reason.isnot(None)
            )
            if start_date:
                reason_counts = reason_counts.filter(HumanFeedbackModel.created_at >= start_date)
            if end_date:
                reason_counts = reason_counts.filter(HumanFeedbackModel.created_at <= end_date)

            reason_counts = reason_counts.group_by(HumanFeedbackModel.override_reason).all()
            for reason, count in reason_counts:
                if reason:
                    stats.override_reasons[reason] = count

            # Outcome tracking
            stats.outcomes_tracked = query.filter(
                HumanFeedbackModel.outcome.isnot(None)
            ).count()

            return stats
        finally:
            session.close()

    async def update_outcome(
        self,
        result_id: str,
        final_outcome: str,
        outcome_timestamp: datetime,
        notes: str = ""
    ) -> bool:
        """Update feedback with final outcome."""
        from database.models import HumanFeedback as HumanFeedbackModel

        session = self._get_session()
        try:
            model = session.query(HumanFeedbackModel).filter(
                HumanFeedbackModel.result_id == result_id
            ).first()

            if model:
                model.outcome = final_outcome
                model.outcome_recorded_at = outcome_timestamp
                if notes:
                    model.notes = (model.notes or "") + f"\n\nOutcome: {notes}"
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating outcome: {e}")
            raise
        finally:
            session.close()

    async def count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        decision_type: Optional[str] = None
    ) -> int:
        """Count matching feedback entries."""
        from database.models import HumanFeedback as HumanFeedbackModel

        session = self._get_session()
        try:
            query = session.query(HumanFeedbackModel)

            if start_date:
                query = query.filter(HumanFeedbackModel.created_at >= start_date)
            if end_date:
                query = query.filter(HumanFeedbackModel.created_at <= end_date)
            if decision_type:
                query = query.filter(HumanFeedbackModel.decision_type == decision_type)

            return query.count()
        finally:
            session.close()

"""
Database connection and session management for TrustChain.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator

from database.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    Usage:
        db = DatabaseManager(database_url)
        db.init_db()  # Create tables
        
        with db.get_session() as session:
            # Use session
            pass
    """
    
    def __init__(self, database_url: str, echo: bool = False):
        """
        Initialize database manager.
        
        Args:
            database_url: PostgreSQL connection string
            echo: Whether to log SQL queries
        """
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=10,
            max_overflow=20
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Database manager initialized")
    
    def init_db(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")
    
    def drop_all(self):
        """Drop all database tables (use with caution!)."""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All database tables dropped")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session with automatic cleanup.
        
        Yields:
            SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """
        Get session without context manager (for dependency injection).
        
        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()


# Global database manager instance
_db_manager: DatabaseManager = None


def init_database(database_url: str, echo: bool = False) -> DatabaseManager:
    """
    Initialize global database manager.
    
    Args:
        database_url: PostgreSQL connection string
        echo: Whether to log SQL queries
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url, echo=echo)
    return _db_manager


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager.
    
    Returns:
        DatabaseManager instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager


# FastAPI dependency for session injection
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db session
            pass
    
    Yields:
        SQLAlchemy session
    """
    db_manager = get_db_manager()
    session = db_manager.get_session_direct()
    try:
        yield session
    finally:
        session.close()

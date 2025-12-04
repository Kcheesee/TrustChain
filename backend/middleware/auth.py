"""
TrustChain API Key Authentication

Provides API key-based authentication for service-to-service communication.

Features:
- API key validation via header or query parameter
- Key scoping (read, write, admin)
- Key rotation support
- Audit logging

Usage:
    from middleware.auth import require_api_key, Scope

    @app.get("/api/protected")
    @require_api_key(scopes=[Scope.READ])
    async def protected_endpoint(api_key_info: APIKeyInfo = Depends()):
        return {"message": "Authenticated!"}

Built with care by Kareem & Claude
"""

import os
import logging
import hashlib
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

from fastapi import HTTPException, Security, status, Depends, Request
from fastapi.security import APIKeyHeader, APIKeyQuery

logger = logging.getLogger(__name__)


class Scope(str, Enum):
    """API key permission scopes."""
    READ = "read"           # Read-only access
    WRITE = "write"         # Write access (submit decisions)
    ANALYTICS = "analytics" # Analytics and reporting
    ADMIN = "admin"         # Full administrative access


@dataclass
class APIKeyInfo:
    """Information about an authenticated API key."""
    key_id: str
    client_name: str
    scopes: Set[Scope]
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    rate_limit_per_minute: int = 60
    metadata: Dict = field(default_factory=dict)


@dataclass
class APIKeyRecord:
    """Internal record for API key storage."""
    key_hash: str
    info: APIKeyInfo


class APIKeyAuth:
    """
    API Key Authentication Manager.

    Handles key validation, scope checking, and audit logging.
    """

    # Header and query parameter names
    API_KEY_HEADER = "X-API-Key"
    API_KEY_QUERY = "api_key"

    def __init__(self):
        """Initialize the API key manager."""
        # In production, this would be backed by a database
        self._keys: Dict[str, APIKeyRecord] = {}
        self._key_counter = 0

        # Load master key from environment
        self._load_environment_keys()

    def _load_environment_keys(self):
        """Load API keys from environment variables."""
        master_key = os.getenv("API_KEY")
        if master_key:
            # Register the master key with admin scope
            key_info = APIKeyInfo(
                key_id="master",
                client_name="Environment Master Key",
                scopes={Scope.READ, Scope.WRITE, Scope.ANALYTICS, Scope.ADMIN},
                created_at=datetime.now(),
                rate_limit_per_minute=1000
            )
            key_hash = self._hash_key(master_key)
            self._keys[key_hash] = APIKeyRecord(key_hash=key_hash, info=key_info)
            logger.info("Loaded master API key from environment")

    def _hash_key(self, key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def generate_key(
        self,
        client_name: str,
        scopes: List[Scope],
        rate_limit_per_minute: int = 60,
        metadata: Optional[Dict] = None
    ) -> tuple[str, APIKeyInfo]:
        """
        Generate a new API key.

        Args:
            client_name: Name of the client/service
            scopes: List of permission scopes
            rate_limit_per_minute: Rate limit for this key
            metadata: Additional metadata

        Returns:
            Tuple of (raw_key, key_info)
        """
        self._key_counter += 1
        key_id = f"tc_key_{self._key_counter}_{secrets.token_hex(4)}"

        # Generate secure random key
        raw_key = f"tc_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)

        key_info = APIKeyInfo(
            key_id=key_id,
            client_name=client_name,
            scopes=set(scopes),
            created_at=datetime.now(),
            rate_limit_per_minute=rate_limit_per_minute,
            metadata=metadata or {}
        )

        self._keys[key_hash] = APIKeyRecord(key_hash=key_hash, info=key_info)

        logger.info(f"Generated new API key: {key_id} for {client_name}")
        return raw_key, key_info

    def validate_key(self, raw_key: str) -> Optional[APIKeyInfo]:
        """
        Validate an API key.

        Args:
            raw_key: The raw API key string

        Returns:
            APIKeyInfo if valid, None otherwise
        """
        if not raw_key:
            return None

        key_hash = self._hash_key(raw_key)
        record = self._keys.get(key_hash)

        if not record:
            logger.warning(f"Invalid API key attempted")
            return None

        if not record.info.is_active:
            logger.warning(f"Inactive API key used: {record.info.key_id}")
            return None

        # Update last used
        record.info.last_used = datetime.now()

        return record.info

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key by its ID.

        Args:
            key_id: The key ID to revoke

        Returns:
            True if revoked, False if not found
        """
        for record in self._keys.values():
            if record.info.key_id == key_id:
                record.info.is_active = False
                logger.info(f"Revoked API key: {key_id}")
                return True
        return False

    def check_scope(self, key_info: APIKeyInfo, required_scopes: List[Scope]) -> bool:
        """
        Check if a key has the required scopes.

        Args:
            key_info: The API key info
            required_scopes: List of required scopes

        Returns:
            True if key has all required scopes
        """
        # Admin scope grants all permissions
        if Scope.ADMIN in key_info.scopes:
            return True

        return all(scope in key_info.scopes for scope in required_scopes)

    def list_keys(self) -> List[APIKeyInfo]:
        """List all registered API keys (without revealing the actual keys)."""
        return [record.info for record in self._keys.values()]

    def get_key_info(self, key_id: str) -> Optional[APIKeyInfo]:
        """Get info about a specific key by ID."""
        for record in self._keys.values():
            if record.info.key_id == key_id:
                return record.info
        return None


# Global API key manager instance
api_key_auth = APIKeyAuth()

# FastAPI security dependencies
api_key_header = APIKeyHeader(name=APIKeyAuth.API_KEY_HEADER, auto_error=False)
api_key_query = APIKeyQuery(name=APIKeyAuth.API_KEY_QUERY, auto_error=False)


async def get_api_key(
    api_key_header: str = Security(api_key_header),
    api_key_query: str = Security(api_key_query),
) -> Optional[str]:
    """Get API key from header or query parameter."""
    return api_key_header or api_key_query


async def get_api_key_info(
    request: Request,
    api_key: str = Depends(get_api_key)
) -> Optional[APIKeyInfo]:
    """
    Validate API key and return info.

    This dependency can be used without requiring authentication
    (returns None if no key provided).
    """
    if not api_key:
        return None

    key_info = api_key_auth.validate_key(api_key)
    if key_info:
        # Attach to request state for rate limiting
        request.state.api_key_info = key_info
    return key_info


def require_api_key(scopes: Optional[List[Scope]] = None):
    """
    Decorator to require API key authentication.

    Args:
        scopes: Optional list of required scopes

    Usage:
        @app.get("/protected")
        @require_api_key(scopes=[Scope.READ])
        async def protected():
            return {"status": "ok"}
    """
    required_scopes = scopes or []

    async def dependency(
        key_info: Optional[APIKeyInfo] = Depends(get_api_key_info)
    ) -> APIKeyInfo:
        if not key_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "ApiKey"}
            )

        if required_scopes and not api_key_auth.check_scope(key_info, required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scopes: {[s.value for s in required_scopes]}"
            )

        return key_info

    return Depends(dependency)

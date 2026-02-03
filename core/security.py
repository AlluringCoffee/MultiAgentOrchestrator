"""
Security module for the Multi-Agent Orchestrator.

Provides:
- API key authentication
- Rate limiting
- Request validation
- Security headers
"""

import os
import time
import hashlib
import secrets
import logging
from typing import Dict, Optional, Callable, Any
from functools import wraps
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============ API Key Management ============

class APIKeyManager:
    """
    Manages API keys for authentication.

    Keys can be provided via:
    1. Environment variable: MAO_API_KEY
    2. Config file: config/api_keys.json
    3. Generated on first run (development mode)
    """

    def __init__(self):
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._enabled = True
        self._load_keys()

    def _load_keys(self):
        """Load API keys from environment or config."""
        # Check environment variable first
        env_key = os.getenv('MAO_API_KEY')
        if env_key:
            self._keys['env'] = {
                'key': env_key,
                'name': 'Environment Key',
                'permissions': ['*']
            }
            logger.info("API key loaded from environment variable")
            return

        # Check config file
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'api_keys.json')
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    for key_id, key_data in data.items():
                        self._keys[key_id] = key_data
                logger.info(f"Loaded {len(self._keys)} API keys from config")
                return
            except Exception as e:
                logger.warning(f"Failed to load API keys from config: {e}")

        # Development mode: disable authentication with warning
        if os.getenv('MAO_DEV_MODE', '').lower() in ('1', 'true', 'yes'):
            self._enabled = False
            logger.warning("!!! DEVELOPMENT MODE: API authentication DISABLED !!!")
            logger.warning("Set MAO_API_KEY environment variable for production")
        else:
            # Generate a random key for first-time setup
            generated_key = secrets.token_urlsafe(32)
            self._keys['generated'] = {
                'key': generated_key,
                'name': 'Auto-generated Key',
                'permissions': ['*']
            }
            logger.warning("=" * 60)
            logger.warning("No API key configured. Generated temporary key:")
            logger.warning(f"  {generated_key}")
            logger.warning("Set MAO_API_KEY environment variable for production")
            logger.warning("=" * 60)

    def is_enabled(self) -> bool:
        """Check if authentication is enabled."""
        return self._enabled

    def validate_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return its metadata.
        Returns None if invalid.
        """
        if not self._enabled:
            return {'name': 'dev-mode', 'permissions': ['*']}

        if not api_key:
            return None

        # Constant-time comparison to prevent timing attacks
        for key_id, key_data in self._keys.items():
            if secrets.compare_digest(key_data['key'], api_key):
                return key_data

        return None

    def has_permission(self, api_key: str, permission: str) -> bool:
        """Check if an API key has a specific permission."""
        key_data = self.validate_key(api_key)
        if not key_data:
            return False

        permissions = key_data.get('permissions', [])
        return '*' in permissions or permission in permissions


# Global instance
api_key_manager = APIKeyManager()


# ============ Rate Limiting ============

class RateLimiter:
    """
    Simple in-memory rate limiter.

    Uses a sliding window approach to limit requests per IP/key.
    """

    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self._requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed for the given identifier.

        Returns:
            (allowed, metadata) where metadata contains rate limit info
        """
        now = time.time()
        window_start = now - 60  # 1 minute window

        # Clean old requests
        self._requests[identifier] = [
            t for t in self._requests[identifier]
            if t > window_start
        ]

        requests_in_window = len(self._requests[identifier])

        # Check burst limit (requests in last second)
        recent_requests = sum(1 for t in self._requests[identifier] if t > now - 1)

        metadata = {
            'limit': self.requests_per_minute,
            'remaining': max(0, self.requests_per_minute - requests_in_window),
            'reset': int(window_start + 60)
        }

        if recent_requests >= self.burst_limit:
            logger.warning(f"Burst limit exceeded for {identifier}")
            return False, metadata

        if requests_in_window >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False, metadata

        # Record this request
        self._requests[identifier].append(now)

        return True, metadata


# Global rate limiter
rate_limiter = RateLimiter()


# ============ Input Validation ============

def validate_path_param(path: str, allow_absolute: bool = False) -> tuple[bool, str]:
    """
    Validate a file path parameter.

    Returns:
        (is_valid, error_message)
    """
    if not path:
        return False, "Empty path"

    # Check for null bytes
    if '\x00' in path:
        return False, "Null byte in path"

    # Check for path traversal
    if '..' in path:
        return False, "Path traversal not allowed"

    # Check for absolute paths
    if not allow_absolute:
        if path.startswith('/') or (len(path) > 1 and path[1] == ':'):
            return False, "Absolute paths not allowed"

    return True, ""


def sanitize_log_message(message: str, max_length: int = 1000) -> str:
    """Sanitize a message for logging (remove sensitive data patterns)."""
    import re

    if not message:
        return ""

    # Truncate
    if len(message) > max_length:
        message = message[:max_length] + "...[truncated]"

    # Mask potential API keys
    message = re.sub(r'(?i)(api[_-]?key|token|password|secret)["\']?\s*[:=]\s*["\']?[\w\-]+',
                     r'\1=***REDACTED***', message)

    # Mask Bearer tokens
    message = re.sub(r'Bearer\s+[\w\-\.]+', 'Bearer ***REDACTED***', message)

    return message


# ============ Security Headers ============

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
}


def get_security_headers() -> Dict[str, str]:
    """Get security headers to add to responses."""
    return SECURITY_HEADERS.copy()


# ============ FastAPI Integration ============

def create_auth_dependency():
    """
    Create a FastAPI dependency for API key authentication.

    Usage:
        from fastapi import Depends
        from core.security import create_auth_dependency

        auth = create_auth_dependency()

        @app.get("/api/protected")
        async def protected_endpoint(auth_data: dict = Depends(auth)):
            return {"user": auth_data['name']}
    """
    from fastapi import HTTPException, Security
    from fastapi.security import APIKeyHeader

    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

    async def verify_api_key(api_key: str = Security(api_key_header)):
        if not api_key_manager.is_enabled():
            return {'name': 'dev-mode', 'permissions': ['*']}

        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key required. Provide X-API-Key header."
            )

        key_data = api_key_manager.validate_key(api_key)
        if not key_data:
            raise HTTPException(
                status_code=403,
                detail="Invalid API key"
            )

        return key_data

    return verify_api_key


def create_rate_limit_dependency(requests_per_minute: int = 60):
    """
    Create a FastAPI dependency for rate limiting.

    Usage:
        from fastapi import Depends, Request
        from core.security import create_rate_limit_dependency

        rate_limit = create_rate_limit_dependency(30)

        @app.get("/api/limited")
        async def limited_endpoint(request: Request, _: None = Depends(rate_limit)):
            return {"status": "ok"}
    """
    from fastapi import HTTPException, Request

    limiter = RateLimiter(requests_per_minute=requests_per_minute)

    async def check_rate_limit(request: Request):
        # Use client IP as identifier
        client_ip = request.client.host if request.client else "unknown"

        allowed, metadata = limiter.is_allowed(client_ip)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    'X-RateLimit-Limit': str(metadata['limit']),
                    'X-RateLimit-Remaining': str(metadata['remaining']),
                    'X-RateLimit-Reset': str(metadata['reset']),
                    'Retry-After': '60'
                }
            )

        return None

    return check_rate_limit

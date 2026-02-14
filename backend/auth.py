"""
JWT authentication middleware for FastAPI.

Verifies Supabase JWT tokens using JWKS (ES256) public key verification.
"""

import os
from typing import Optional

import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from logger_config import setup_logging
from errors import ErrorCode

logger = setup_logging()


class AuthenticatedUser(BaseModel):
    """Authenticated user information extracted from JWT."""
    id: str
    email: Optional[str] = None
    role: str = "authenticated"


# JWT configuration — uses JWKS endpoint for ES256 public key verification
SUPABASE_URL = os.getenv("SUPABASE_URL")
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    """Lazily initialize and cache the JWKS client."""
    global _jwks_client
    if _jwks_client is None:
        if not SUPABASE_URL:
            raise RuntimeError("SUPABASE_URL not configured")
        _jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    return _jwks_client


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> AuthenticatedUser:
    """
    FastAPI dependency to extract and verify the JWT token.

    Usage:
        @app.get("/protected")
        async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
            return {"user_id": user.id}

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": ErrorCode.UNAUTHORIZED.value,
                    "message": "Authorization header required",
                    "category": "authentication",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": ErrorCode.UNAUTHORIZED.value,
                    "message": "Invalid authorization header format. Use: Bearer <token>",
                    "category": "authentication",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    if not SUPABASE_URL:
        logger.error("SUPABASE_URL not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Authentication not configured",
                    "category": "internal",
                }
            },
        )

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",  # Supabase default audience
        )

        # Extract user info from Supabase JWT claims
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": ErrorCode.UNAUTHORIZED.value,
                        "message": "Invalid token: missing user ID",
                        "category": "authentication",
                    }
                },
            )

        return AuthenticatedUser(
            id=user_id,
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
        )

    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": ErrorCode.TOKEN_EXPIRED.value,
                    "message": "Token has expired. Please sign in again.",
                    "category": "authentication",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": ErrorCode.UNAUTHORIZED.value,
                    "message": "Invalid authentication token",
                    "category": "authentication",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[AuthenticatedUser]:
    """
    Optional authentication - returns None if no token provided.

    Useful for endpoints that work both authenticated and anonymously.
    """
    if not authorization:
        return None

    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None

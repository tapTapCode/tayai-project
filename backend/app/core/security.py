"""
Security utilities for authentication and authorization

Provides:
- Password hashing and verification using bcrypt
- JWT access token creation and validation
- Refresh token support for extended sessions
- Token type differentiation (access vs refresh)
"""
from datetime import datetime, timedelta
from typing import Optional, Literal
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token types for differentiation
TokenType = Literal["access", "refresh"]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data (user_id, username, tier, etc.)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT access token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow(),
    })
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token.
    
    Refresh tokens have longer expiration and are used to obtain new access tokens.
    
    Args:
        data: Minimal payload (user_id only for security)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = {
        "user_id": data.get("user_id"),
        "jti": secrets.token_urlsafe(16),  # Unique token ID for revocation
    }
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow(),
    })
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: The JWT token string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        # Verify it's an access token (or legacy token without type)
        token_type = payload.get("type", "access")
        if token_type != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT refresh token.
    
    Args:
        token: The JWT refresh token string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token.
    
    Args:
        email: User's email address
        
    Returns:
        Encoded JWT token for password reset
    """
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "email": email,
        "type": "password_reset",
        "exp": expire,
    }
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token and return the email.
    
    Args:
        token: The password reset token
        
    Returns:
        Email address or None if invalid
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "password_reset":
            return None
        return payload.get("email")
    except JWTError:
        return None

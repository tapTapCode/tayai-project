"""
Authentication Schemas

Defines request/response schemas for authentication endpoints.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class Token(BaseModel):
    """Token response schema with both access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiration in seconds")


class TokenRefreshRequest(BaseModel):
    """Request schema for token refresh."""
    refresh_token: str


class TokenData(BaseModel):
    """Decoded token data schema."""
    sub: Optional[str] = None
    user_id: Optional[int] = None
    tier: Optional[str] = None
    is_admin: Optional[bool] = False


class UserLogin(BaseModel):
    """User login request schema."""
    username: str
    password: str


class UserVerify(BaseModel):
    """User verification response schema."""
    valid: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    tier: Optional[str] = None
    is_admin: Optional[bool] = False


class UserCreate(BaseModel):
    """User registration request schema."""
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    """User response schema (excludes sensitive data)."""
    id: int
    email: str
    username: str
    tier: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    profile_data: Optional[dict] = None  # External profile data from membership platform
    
    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Extended user profile with membership platform data."""
    user_id: int
    email: str
    username: str
    tier: str
    profile_image_url: Optional[str] = None
    full_name: Optional[str] = None
    enrolled_courses: Optional[list] = None
    membership_start_date: Optional[datetime] = None
    last_active: Optional[datetime] = None
    metadata: Optional[dict] = None  # Additional platform-specific data


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    token: str
    new_password: str = Field(min_length=8)


class PasswordChange(BaseModel):
    """Password change request schema (for authenticated users)."""
    current_password: str
    new_password: str = Field(min_length=8)


class SSORequest(BaseModel):
    """SSO authentication request from membership platform."""
    platform_token: str = Field(description="JWT or session token from membership platform")
    platform: str = Field(default="custom", description="Platform identifier (skool, custom)")
    email: Optional[EmailStr] = Field(None, description="User email (optional, can be extracted from token)")

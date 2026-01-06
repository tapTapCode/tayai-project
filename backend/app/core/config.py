"""
Application Configuration

Loads environment variables from .env file and provides
typed configuration settings for the application.
"""
from dotenv import load_dotenv

# Load .env file BEFORE any os.getenv() calls
load_dotenv()

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    PROJECT_NAME: str = "TayAI"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://tayai_user:tayai_password@localhost:5432/tayai_db"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_EMBEDDING_MODEL: str = os.getenv(
        "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    
    # Usage Limits
    BASIC_MEMBER_MESSAGES_PER_MONTH: int = int(
        os.getenv("BASIC_MEMBER_MESSAGES_PER_MONTH", "50")
    )  # Trial tier - 7 days access
    VIP_MEMBER_MESSAGES_PER_MONTH: int = int(
        os.getenv("VIP_MEMBER_MESSAGES_PER_MONTH", "1000")
    )  # Elite tier - Full access
    
    # Trial Period
    TRIAL_PERIOD_DAYS: int = int(os.getenv("TRIAL_PERIOD_DAYS", "7"))
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    
    # Membership Platform
    MEMBERSHIP_PLATFORM_API_URL: str = os.getenv("MEMBERSHIP_PLATFORM_API_URL", "")
    MEMBERSHIP_PLATFORM_API_KEY: str = os.getenv("MEMBERSHIP_PLATFORM_API_KEY", "")
    
    # Upgrade URLs (for usage limit exceeded prompts)
    UPGRADE_URL_BASIC: str = os.getenv(
        "UPGRADE_URL_BASIC",
        "https://www.skool.com/tla-hair-hutlers-co/about"
    )  # Hair Hu$tlers Co - $37/month
    UPGRADE_URL_VIP: str = os.getenv(
        "UPGRADE_URL_VIP",
        "https://www.skool.com/tla-hair-hutlers-co/about"
    )  # Hair Hu$tlers ELITE (update with actual URL)
    UPGRADE_URL_GENERIC: str = os.getenv(
        "UPGRADE_URL_GENERIC",
        "https://www.skool.com/tla-hair-hutlers-co/about"
    )
    
    # Membership Pricing
    BASIC_MEMBERSHIP_PRICE: str = os.getenv("BASIC_MEMBERSHIP_PRICE", "$37")  # Hair Hu$tlers Co
    VIP_MEMBERSHIP_PRICE: str = os.getenv("VIP_MEMBERSHIP_PRICE", "")  # Hair Hu$tlers ELITE pricing
    
    # Skool Integration
    SKOOL_WEBHOOK_SECRET: str = os.getenv("SKOOL_WEBHOOK_SECRET", "")
    SKOOL_COMMUNITY_URL: str = os.getenv(
        "SKOOL_COMMUNITY_URL",
        "https://www.skool.com/tla-hair-hutlers-co"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

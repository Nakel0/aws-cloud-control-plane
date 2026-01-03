"""
Application configuration using Pydantic Settings
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    app_name: str = "CloudGuard"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # API
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # AWS Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_assume_role_arn: Optional[str] = None
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cloudguard"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Scanning
    scan_interval_hours: int = 6
    max_concurrent_scans: int = 10
    
    # Cost Thresholds
    idle_resource_days: int = 7
    low_utilization_threshold: float = 10.0  # CPU percentage
    
    # Security Thresholds
    public_bucket_severity: str = "critical"
    unencrypted_resource_severity: str = "high"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

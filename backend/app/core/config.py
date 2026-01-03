"""
Application configuration management
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "CloudGuard"
    ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    API_VERSION: str = "v1"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Redis
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 3600
    
    # RabbitMQ & Celery
    RABBITMQ_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # AWS
    AWS_DEFAULT_REGION: str = "us-east-1"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_PORT: int = 9090
    
    # Feature Flags
    ENABLE_AUTOMATION: bool = True
    ENABLE_AUTO_REMEDIATION: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

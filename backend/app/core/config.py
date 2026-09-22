"""Application configuration and environment settings management."""

from functools import lru_cache
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Environment
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    DEBUG: bool = Field(default=True, description="Debug flag")
    APP_NAME: str = Field(
        default="AI Resume Intelligence & Job Alignment Engine",
        description="Application display name",
    )
    APP_VERSION: str = Field(default="1.0.0", description="Semantic application version")
    API_V1_STR: str = Field(default="/api/v1", description="API v1 route prefix")

    # Network Binding
    HOST: str = Field(default="0.0.0.0", description="Host address")
    PORT: int = Field(default=8000, description="Listening port")

    # Security & Tokens
    SECRET_KEY: str = Field(
        default="dev-secret-key-never-use-in-production-must-override-via-env",
        description="Cryptographic secret key for signing tokens",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, description="Access token expiration in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Refresh token expiration in days"
    )

    # CORS
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        description="Allowed CORS origins",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Persistence
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./storage/irecruit.db",
        description="Async database connection string",
    )

    # Storage & Upload limits
    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=5 * 1024 * 1024,  # 5 MB
        description="Maximum allowed resume upload size in bytes",
    )
    UPLOAD_TEMP_DIR: str = Field(
        default="./storage/temp",
        description="Temporary file directory for document processing",
    )

    # AI Provider Defaults
    DEFAULT_LLM_PROVIDER: str = Field(
        default="mock", description="Default LLM provider (mock, openai, ollama)"
    )
    DEFAULT_LLM_MODEL: str = Field(
        default="mock-model", description="Default LLM model identifier"
    )
    DEFAULT_EMBEDDING_PROVIDER: str = Field(
        default="mock",
        description="Default embedding provider (mock, openai, local)",
    )
    DEFAULT_EMBEDDING_MODEL: str = Field(
        default="mock-embedding", description="Default embedding model identifier"
    )

    # External Provider Config (Optional)
    OPENAI_API_KEY: str | None = Field(
        default=None, description="OpenAI API Key (if using OpenAI)"
    )
    OPENAI_BASE_URL: str = Field(
        default="https://api.openai.com/v1", description="OpenAI API Base URL"
    )
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434", description="Ollama API base URL"
    )

    # Privacy & Retention
    ANONYMOUS_DATA_RETENTION_HOURS: int = Field(
        default=24, description="Retention limit for anonymous analysis"
    )
    AUDIT_LOG_ENABLED: bool = Field(
        default=True, description="Enable structured audit event logging"
    )
    PII_REDACTION_ENABLED: bool = Field(
        default=True, description="Enable automated PII minimization"
    )

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE_ANONYMOUS: int = Field(
        default=10, description="Requests per minute allowed for anonymous clients"
    )
    RATE_LIMIT_PER_MINUTE_AUTHENTICATED: int = Field(
        default=60, description="Requests per minute allowed for authenticated users"
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton provider."""
    return Settings()

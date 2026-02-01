"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars that don't match field names
    )

    # Application
    app_name: str = "AI Internal Manager"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_manager"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_conversation_ttl: int = 3600  # 1 hour

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = Field(default=SecretStr("password123"))

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_prefix: str = "ai_manager"

    # Anthropic
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))
    anthropic_default_model: str = "claude-3-5-sonnet-20241022"
    anthropic_fast_model: str = "claude-3-5-haiku-20241022"  # For classification/simple tasks
    anthropic_reasoning_model: str = "claude-3-opus-20240229"
    anthropic_max_tokens: int = 4096

    # Keywords AI
    keywords_ai_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("keywords_ai_api_key", "keywordsai_api_key"),
    )
    keywords_ai_base_url: str = Field(
        default="https://api.keywordsai.co/api/",
        validation_alias=AliasChoices("keywords_ai_base_url", "keywordsai_base_url"),
    )
    keywords_ai_default_model: str = "gpt-4o"  # Default to GPT-4o for broader compatibility

    # Keywords AI Caching
    keywords_ai_cache_enabled: bool = True
    keywords_ai_cache_ttl: int = 86400  # 24 hours in seconds (default is 30 days)
    keywords_ai_cache_by_customer: bool = True  # Cache per customer identifier

    # LLM Provider
    llm_provider: Literal["anthropic", "keywords_ai"] = "anthropic"

    # Embeddings
    embedding_provider: Literal["voyage", "openai"] = "voyage"
    voyage_api_key: SecretStr = Field(default=SecretStr(""))
    voyage_model: str = "voyage-large-2"
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    openai_embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 1536  # voyage-large-2 produces 1536 dimensions

    # Voice
    deepgram_api_key: SecretStr = Field(default=SecretStr(""))
    elevenlabs_api_key: SecretStr = Field(default=SecretStr("sk_d7ca2cd289670ae397f0f0ac7a2e70d3b2dc85d963bed00f"))
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

    # Zoom Integration
    zoom_client_id: str = "MOi1sFS0RmyeVM8NYFk17w"
    zoom_client_secret: SecretStr = Field(default=SecretStr("kvh4S5XK7WugtYUXO5qhhTRHAqz79o5Z"))
    zoom_account_id: str = "Sc3YAF-4T2SQ5dqlGieKPg"
    zoom_bot_jid: str = ""
    zoom_webhook_secret: str = ""

    # External Services (MCP Connectors)
    jira_base_url: str = ""
    jira_api_token: SecretStr = Field(default=SecretStr(""))
    jira_email: str = ""

    github_token: SecretStr = Field(default=SecretStr(""))
    github_org: str = ""

    slack_bot_token: SecretStr = Field(default=SecretStr(""))
    slack_app_token: SecretStr = Field(default=SecretStr(""))

    # Auth
    jwt_secret_key: SecretStr = Field(default=SecretStr("your-super-secret-jwt-key-change-in-production"))
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Observability
    log_level: str = "INFO"
    enable_tracing: bool = True
    otlp_endpoint: str = "http://localhost:4317"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration for Lawgic.

    Configuration values are loaded from:
    1. Environment variables
    2. .env file
    3. Default values defined below
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # =========================================================
    # Application
    # =========================================================

    app_name: str = Field(
        default="Lawgic",
        alias="APP_NAME",
    )

    environment: str = Field(
        default="development",
        alias="ENVIRONMENT",
    )

    # =========================================================
    # Logging
    # =========================================================

    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )

    # =========================================================
    # Vector Database
    # =========================================================

    vector_db_path: Path = Field(
        default=Path("vector_db"),
        alias="VECTOR_DB_PATH",
    )

    chroma_collection: str = Field(
        default="legal_chunks",
        alias="CHROMA_COLLECTION",
    )

    # =========================================================
    # Embedding Model
    # =========================================================

    embedding_model_name: str = Field(
        default="BAAI/bge-small-en",
        alias="EMBEDDING_MODEL_NAME",
    )

    embedding_model_local_path: str | None = Field(
        default=None,
        alias="EMBEDDING_MODEL_LOCAL_PATH",
    )

    # =========================================================
    # Legal Model
    # =========================================================

    legal_model_name: str = Field(
        default="law-ai/CustomInLawBERT",
        alias="LEGAL_MODEL_NAME",
    )

    legal_model_local_path: str | None = Field(
        default=None,
        alias="LEGAL_MODEL_LOCAL_PATH",
    )

    # =========================================================
    # Ollama
    # =========================================================

    ollama_model: str = Field(
        default="gpt-oss:120b",
        alias="OLLAMA_MODEL",
    )

    llm_provider: str = Field(
        default="ollama",
        alias="LLM_PROVIDER",
    )

    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL",
    )

    # =========================================================
    # Frontend / Backend URLs
    # =========================================================

    frontend_base_url: str = Field(
        default="http://localhost:5173",
        alias="FRONTEND_BASE_URL",
    )

    backend_base_url: str = Field(
        default="http://localhost:8000",
        alias="BACKEND_BASE_URL",
    )

    backend_public_url: str = Field(
        default="http://localhost:8000",
        alias="BACKEND_PUBLIC_URL",
    )

    # =========================================================
    # Google Authentication
    # =========================================================

    google_client_id: str | None = Field(
        default=None,
        alias="GOOGLE_CLIENT_ID",
    )

    google_client_secret: str | None = Field(
        default=None,
        alias="GOOGLE_CLIENT_SECRET",
    )

    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )

    # =========================================================
    # Authentication
    # =========================================================

    auth_secret: str = Field(
        default="change-this-secret-in-production",
        alias="AUTH_SECRET",
    )

    auth_token_ttl_seconds: int = Field(
        default=86400,
        alias="AUTH_TOKEN_TTL_SECONDS",
    )

    # =========================================================
    # OCR
    # =========================================================

    tesseract_cmd: str | None = Field(
        default=None,
        alias="TESSERACT_CMD",
    )

    ocr_dpi: int = Field(
        default=300,
        alias="OCR_DPI",
    )

    ocr_lang: str = Field(
        default="eng",
        alias="OCR_LANG",
    )

    # =========================================================
    # Upload Configuration
    # =========================================================

    max_upload_size_mb: int = Field(
        default=25,
        alias="MAX_UPLOAD_SIZE_MB",
    )

    # =========================================================
    # Retrieval Configuration
    # =========================================================

    retrieval_top_k: int = Field(
        default=5,
        alias="RETRIEVAL_TOP_K",
    )


# =============================================================
# Global Settings Instance
# =============================================================

settings = Settings()


# =============================================================
# Settings Getter
# =============================================================

def get_settings() -> Settings:
    """
    Return the application settings instance.
    """

    return settings
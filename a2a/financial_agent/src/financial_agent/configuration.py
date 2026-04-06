"""Configuration for the Financial Agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    """Environment-based configuration.

    Loads, in order (later wins): `.env.lmstudio` then `.env`.
    Use `.env.lmstudio` as the checked-in local template; override with `.env` if needed.
    """

    model_config = SettingsConfigDict(
        env_file=(".env.lmstudio", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_model: str = "qwen/qwen3-30b-a3b-2507"
    llm_api_base: str = "http://localhost:1234/v1"
    llm_api_key: str = "not-needed"
    mcp_url: str = "http://localhost:8000/mcp"
    mcp_transport: str = "streamable_http"
    port: int = 8000
    # SQLite avoids MLflow FutureWarning on deprecated file-store ./mlruns (Feb 2026+)
    mlflow_tracking_uri: str = "sqlite:///./mlflow.db"
    mlflow_experiment_name: str = "financial-agent"

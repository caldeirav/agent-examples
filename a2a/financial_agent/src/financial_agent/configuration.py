"""Configuration for the Financial Agent."""

from pydantic_settings import BaseSettings


class Configuration(BaseSettings):
    """Environment-based configuration."""

    llm_model: str = "qwen/qwen3-30b-a3b-2507"
    llm_api_base: str = "http://localhost:1234/v1"
    llm_api_key: str = "not-needed"
    mcp_url: str = "http://localhost:8000/mcp"
    mcp_transport: str = "streamable_http"
    mlflow_tracking_uri: str = "./mlruns"
    mlflow_experiment_name: str = "financial-agent"

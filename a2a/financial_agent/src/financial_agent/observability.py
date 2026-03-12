"""MLflow tracing integration for the Financial Agent."""

import os
from typing import Optional

_tracing_initialized = False


def setup_mlflow_tracing(
    tracking_uri: Optional[str] = None,
    experiment_name: Optional[str] = None,
    enable_autolog: bool = True,
) -> bool:
    """
    Configure MLflow tracing for agent observability.

    Args:
        tracking_uri: MLflow tracking URI (default: ./mlruns)
        experiment_name: Experiment name (default: financial-agent)
        enable_autolog: Enable LangChain autologging for traces

    Returns:
        True if tracing was configured successfully
    """
    global _tracing_initialized

    if _tracing_initialized:
        return True

    tracking_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "./mlruns")
    experiment_name = experiment_name or os.getenv(
        "MLFLOW_EXPERIMENT_NAME", "financial-agent"
    )

    try:
        import mlflow

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

        if enable_autolog:
            try:
                mlflow.langchain.autolog()
            except Exception:
                pass  # MLflow may not have langchain integration in all versions

        _tracing_initialized = True
        return True
    except ImportError:
        return False

"""MLflow tracing integration for the Financial Agent."""

import logging
import os
import warnings
from typing import Optional

logger = logging.getLogger(__name__)

_tracing_initialized = False
_mlflow_autolog_noise_filter_installed = False


class _SuppressMlflowAsyncContextVarAutologFilter(logging.Filter):
    """
    MLflow LangChain autolog wraps callbacks in try/except and logs WARNING on any error
    (mlflow.utils.autologging_utils.safety.exception_safe_function_for_class). Async LangGraph
    + MlflowLangchainTracer can hit ContextVar/Token mismatch (github.com/mlflow/mlflow/issues/22088),
    which spams the console though the agent still completes. Drop only those known messages.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno != logging.WARNING:
            return True
        msg = record.getMessage()
        if "Encountered unexpected error during autologging" not in msg:
            return True
        if "was created in a different Context" in msg:
            return False
        return True


def _install_mlflow_autolog_noise_filter() -> None:
    global _mlflow_autolog_noise_filter_installed
    if _mlflow_autolog_noise_filter_installed:
        return
    autolog_log = logging.getLogger("mlflow.utils.autologging_utils")
    autolog_log.addFilter(_SuppressMlflowAsyncContextVarAutologFilter())
    _mlflow_autolog_noise_filter_installed = True


def setup_mlflow_tracing(
    tracking_uri: Optional[str] = None,
    experiment_name: Optional[str] = None,
    enable_autolog: bool = True,
) -> bool:
    """
    Configure MLflow tracing for agent observability.

    Uses ``mlflow.langchain.autolog()``, which patches LangChain's callback manager so
    LLM/tool spans are recorded as MLflow **Traces**. The ``langchain`` PyPI package must
    be installed (not only ``langchain-core``): MLflow imports ``langchain`` for version
    validation before enabling autolog.

    Args:
        tracking_uri: MLflow tracking URI (default from env or sqlite:///./mlflow.db)
        experiment_name: Experiment name (default from env or financial-agent)
        enable_autolog: Enable LangChain autologging for traces

    Returns:
        True if tracing was configured successfully
    """
    global _tracing_initialized

    if _tracing_initialized:
        return True

    _install_mlflow_autolog_noise_filter()

    # MLflow 3.x deprecates plain ./mlruns file store (FutureWarning on every import path)
    warnings.filterwarnings(
        "ignore",
        message=".*filesystem tracking backend.*",
        category=FutureWarning,
        module=r"mlflow\.tracking\._tracking_service\.utils",
    )

    tracking_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "sqlite:///./mlflow.db")
    experiment_name = experiment_name or os.getenv("MLFLOW_EXPERIMENT_NAME", "financial-agent")

    log_traces = os.getenv("MLFLOW_LANGCHAIN_LOG_TRACES", "true").lower() in (
        "1",
        "true",
        "yes",
    )

    try:
        import mlflow

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

        if enable_autolog:
            try:
                # run_tracer_inline=True: recommended for LangGraph async + nested @mlflow.trace.
                # ContextVar noise from mlflow#22088 is filtered above (async MCP tools require astream).
                mlflow.langchain.autolog(
                    run_tracer_inline=True,
                    log_traces=log_traces,
                )
                if log_traces:
                    logger.info(
                        "MLflow LangChain autolog enabled (traces → experiment %s)",
                        experiment_name,
                    )
                else:
                    logger.info(
                        "MLflow experiment %s active; LangChain trace autolog disabled "
                        "(MLFLOW_LANGCHAIN_LOG_TRACES)",
                        experiment_name,
                    )
            except Exception as e:
                logger.warning(
                    "MLflow LangChain autolog failed (%s). Traces will not appear until this "
                    "succeeds (install `langchain`, check versions).",
                    e,
                )

        _tracing_initialized = True
        return True
    except ImportError:
        logger.warning("mlflow not installed; tracing disabled")
        return False

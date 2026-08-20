from fastapi import FastAPI

from app.core.config import settings
from app.observability.logging import configure_logging
from app.observability.metrics import register_metrics_endpoint
from app.observability.middleware import ObservabilityMiddleware
from app.observability.tracing import setup_tracing


def setup_observability(app: FastAPI) -> None:
    configure_logging()

    if settings.prometheus_enabled:
        register_metrics_endpoint(app)

    app.add_middleware(ObservabilityMiddleware)

    if settings.otel_enabled:
        setup_tracing(app)

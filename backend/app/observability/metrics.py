import functools
import time
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.core.config import settings

HTTP_REQUESTS = Counter(
    "aero_http_requests_total",
    "HTTP requests processed",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "aero_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

ARTIFACT_OPERATIONS = Counter(
    "aero_artifact_operations_total",
    "Artifact business operations completed",
    ["operation", "status"],
)

ARTIFACT_OPERATION_DURATION = Histogram(
    "aero_artifact_operation_duration_seconds",
    "Artifact business operation latency",
    ["operation"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

P = ParamSpec("P")
R = TypeVar("R")


def track_artifact_operation(
    operation: str,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(
        func: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            status = "success"
            try:
                return await func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                ARTIFACT_OPERATIONS.labels(operation=operation, status=status).inc()
                ARTIFACT_OPERATION_DURATION.labels(operation=operation).observe(
                    time.perf_counter() - start
                )

        return wrapper

    return decorator


def register_metrics_endpoint(app: FastAPI) -> None:
    @app.get(settings.prometheus_path, include_in_schema=False)
    async def metrics() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

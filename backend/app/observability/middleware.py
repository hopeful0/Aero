import time
import uuid

import structlog
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.observability.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS

_IGNORED_PATHS = {"/healthz", "/readyz"}


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)

        if settings.otel_enabled:
            span_ctx = trace.get_current_span().get_span_context()
            if span_ctx.is_valid:
                structlog.contextvars.bind_contextvars(
                    trace_id=f"{span_ctx.trace_id:032x}",
                    span_id=f"{span_ctx.span_id:016x}",
                )

        start = time.perf_counter()
        logger = structlog.get_logger("aero.request")
        raw_path = request.url.path
        logger.info("request.start", method=request.method, path=raw_path)

        status_code = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request.error",
                method=request.method,
                path=raw_path,
                duration_ms=duration_ms,
            )
            raise
        finally:
            duration = time.perf_counter() - start
            duration_ms = round(duration * 1000, 2)

            route = request.scope.get("route")
            route_path = getattr(route, "path", None) or "UNMATCHED"

            if (
                settings.prometheus_enabled
                and route_path not in _IGNORED_PATHS
                and route_path != settings.prometheus_path
            ):
                HTTP_REQUESTS.labels(
                    method=request.method, path=route_path, status=str(status_code)
                ).inc()
                HTTP_REQUEST_DURATION.labels(
                    method=request.method, path=route_path, status=str(status_code)
                ).observe(duration)

            if status_code < 500:
                logger.info(
                    "request.end",
                    method=request.method,
                    path=raw_path,
                    route=route_path,
                    status=status_code,
                    duration_ms=duration_ms,
                )

            structlog.contextvars.clear_contextvars()

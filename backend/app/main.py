import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api.v1.admin import router as admin_router
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.lineage import router as lineage_router
from app.core.config import settings
from app.core.errors import AeroError
from app.observability import setup_observability
from app.skills import SKILL_MD


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


app = FastAPI(title="Aero API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AeroError)
async def aero_error_handler(request: Request, exc: AeroError) -> JSONResponse:
    structlog.get_logger("aero.error").warning(
        "aero_error",
        code=exc.code,
        status=exc.status,
        method=request.method,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status,
        content=error_body(exc.code, exc.message, exc.details),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_map = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT"}
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(code, str(exc.detail), None),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body(
            "VALIDATION_ERROR",
            "request validation failed",
            {"errors": exc.errors()},
        ),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    structlog.get_logger("aero.error").exception(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content=error_body("INTERNAL", "internal error", None),
    )


prefix = settings.api_prefix
app.include_router(auth_router, prefix=prefix)
app.include_router(admin_router, prefix=prefix)
app.include_router(artifacts_router, prefix=prefix)
app.include_router(feedback_router, prefix=prefix)
app.include_router(lineage_router, prefix=prefix)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "aero-backend", "env": settings.env}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/skill")
async def get_skill() -> Response:
    return Response(content=SKILL_MD, media_type="text/markdown")


setup_observability(app)

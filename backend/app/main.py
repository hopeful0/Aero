from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title="Aero API", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "aero-backend", "env": settings.env}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ok"}

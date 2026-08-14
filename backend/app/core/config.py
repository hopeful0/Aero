from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AERO_", env_file=".env", extra="ignore")

    env: str = "dev"

    postgres_dsn: str = "postgresql+asyncpg://aero:aero@localhost:5432/aero"
    redis_url: str = "redis://localhost:6379/0"

    api_prefix: str = "/api/v1"

    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 2


settings = Settings()

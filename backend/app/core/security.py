import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def hash_token(token: str) -> str:
    return _hasher.hash(token)


def verify_token(token_hash: str, token: str) -> bool:
    try:
        return _hasher.verify(token_hash, token)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def generate_token_secret() -> str:
    return secrets.token_urlsafe(32)


def generate_agent_token(agent_id: str) -> tuple[str, str]:
    secret = generate_token_secret()
    token = f"{agent_id}.{secret}"
    return token, secret


def parse_agent_token(token: str) -> tuple[str, str]:
    if "." not in token:
        raise ValueError("invalid token format")
    agent_id, secret = token.split(".", 1)
    if not agent_id or not secret:
        raise ValueError("invalid token format")
    return agent_id, secret

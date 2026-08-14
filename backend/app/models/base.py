import secrets
import time
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def generate_ulid() -> str:
    ms = int(time.time() * 1000)
    raw = ms.to_bytes(6, "big") + secrets.token_bytes(10)
    val = int.from_bytes(raw, "big")
    chars = []
    for _ in range(26):
        chars.append(_CROCKFORD[val & 0x1F])
        val >>= 5
    return "".join(reversed(chars))


def generate_business_id(prefix: str) -> str:
    return f"{prefix}_{generate_ulid()}"


class Base(DeclarativeBase):
    pass


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

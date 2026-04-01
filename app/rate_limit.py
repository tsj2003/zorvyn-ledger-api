import os
from slowapi import Limiter
from slowapi.util import get_remote_address

_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    enabled=_enabled,
)

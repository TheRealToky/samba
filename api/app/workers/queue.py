"""Queue accessor shared by the API (enqueue) and worker (consume)."""
from __future__ import annotations

from functools import lru_cache

from redis import Redis
from rq import Queue

from app.config import settings

QUEUE_NAME = "samba"


@lru_cache(maxsize=1)
def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=Redis.from_url(settings.redis_url))

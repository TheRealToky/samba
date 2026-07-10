"""Data-processing worker entrypoint (deployment diagram: "Data Processing
Workers"). Runs as: python -m app.workers.worker
"""
from __future__ import annotations

from redis import Redis
from rq import Queue, Worker

from app.config import settings

QUEUE_NAME = "samba"


def main() -> None:
    connection = Redis.from_url(settings.redis_url)
    queue = Queue(QUEUE_NAME, connection=connection)
    print(f"[worker] listening on queue {QUEUE_NAME!r} via {settings.redis_url}", flush=True)
    Worker([queue], connection=connection).work(with_scheduler=True)


if __name__ == "__main__":
    main()

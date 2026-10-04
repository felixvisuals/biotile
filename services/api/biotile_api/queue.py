"""Job dispatch: in-process thread pool (default, no Redis needed) or RQ (docker compose)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .settings import get_settings

_pool: ThreadPoolExecutor | None = None
TASKS = {"generate": "biotile_worker.tasks.generate", "export": "biotile_worker.tasks.export"}


def enqueue(kind: str, job_id: str) -> None:
    s = get_settings()
    if s.queue_backend == "rq":
        from redis import Redis
        from rq import Queue

        Queue("biotile", connection=Redis.from_url(s.redis_url)).enqueue(
            TASKS[kind], job_id, job_timeout=1800)
        return
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="biotile-job")
    from biotile_worker import tasks

    _pool.submit(getattr(tasks, kind), job_id)

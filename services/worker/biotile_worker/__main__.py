"""Run the RQ worker:  python -m biotile_worker"""

import logging

from biotile_api.models import init_db
from biotile_api.settings import get_settings
from redis import Redis
from rq import Queue, Worker


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    s = get_settings()
    init_db()
    conn = Redis.from_url(s.redis_url)
    Worker([Queue("biotile", connection=conn)], connection=conn).work()


if __name__ == "__main__":
    main()

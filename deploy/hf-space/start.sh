#!/bin/sh
# Container start: database, jury invite, demo content (in the background), then the API.
# Secrets (TRIPO_API_KEY, SECRET_KEY) come from the Space settings, never from this repo.
set -e
python -c "from biotile_api.models import init_db; init_db()"
python scripts/invites.py create --code "${JURY_INVITE_CODE:-1852}" --uses 500 --days 60 --note jury || true
( TRIPO_MODE=mock python scripts/seed_demo.py && TRIPO_MODE=mock python scripts/seed_barcelona.py ) \
  > var/seed.log 2>&1 &
exec uvicorn biotile_api.main:app --host 0.0.0.0 --port 7860 --proxy-headers --forwarded-allow-ips="*"

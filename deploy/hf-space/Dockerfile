# Backend image for a Hugging Face Docker Space (free CPU tier). Same as ../../Dockerfile, but
# listens on 7860, runs as uid 1000 and seeds demo content on start (the Space disk is ephemeral).
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock README.md ./
COPY packages ./packages
COPY services ./services
RUN uv sync --frozen --no-dev
COPY scripts ./scripts
COPY data ./data
COPY tests/fixtures ./tests/fixtures
COPY deploy/hf-space/start.sh ./start.sh
RUN mkdir -p /app/var && chown -R 1000:1000 /app
USER 1000
ENV PATH="/app/.venv/bin:$PATH" COOKIE_SECURE=true
EXPOSE 7860
CMD ["sh", "start.sh"]

# API + worker image (Python 3.11, uv)
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
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "biotile_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

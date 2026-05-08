FROM python:3.11-slim

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

WORKDIR /src
COPY --chown=appuser:appuser . .

RUN pip install --no-cache-dir uv && \
    uv sync --frozen

USER appuser


CMD ["sh", "-c", "uv run alembic upgrade head || true && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000"]
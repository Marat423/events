FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG EVENTS_API_KEY
ARG CLIENT_HOST=http://events-provider.dev-2.python-labs.ru
ARG DATABASE_URL=sqlite+aiosqlite:///./local.db

ENV EVENTS_API_KEY=$EVENTS_API_KEY
ENV CLIENT_HOST=$CLIENT_HOST
ENV DATABASE_URL=$DATABASE_URL

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev

COPY --chown=appuser:appuser . .

RUN chown -R appuser:appuser /app

USER appuser

CMD ["/app/.venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

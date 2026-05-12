FROM python:3.11-slim

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser

WORKDIR /src
COPY --chown=appuser:appuser main.py .

USER appuser

CMD ["python", "main.py"]

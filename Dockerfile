# syntax=docker/dockerfile:1
# Only the dependency lockfile and public source enter the build context.
FROM python:3.11-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --python /usr/local/bin/python

FROM python:3.11-slim-bookworm AS runtime
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DLQ_DIR=/app/runtime/dlq
RUN groupadd --gid 10001 extractor \
    && useradd --uid 10001 --gid 10001 --create-home extractor \
    && mkdir -p /app/runtime/dlq \
    && chown -R 10001:10001 /app/runtime
COPY --from=builder /app/.venv /app/.venv
COPY src ./src
COPY samples ./samples
COPY scripts/container_healthcheck.py scripts/inspect_dlq.py ./scripts/
USER 10001:10001
EXPOSE 8000
# Local readiness only; never a provider request or billable extraction.
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD ["python", "scripts/container_healthcheck.py"]
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]

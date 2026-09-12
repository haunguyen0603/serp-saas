FROM python:3.12.12-slim-bookworm AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
COPY backend/pyproject.toml backend/uv.lock ./

FROM base AS development
RUN uv sync --frozen --no-install-project
COPY --chown=app:app backend/ ./
RUN uv sync --frozen && chown -R app:app /app
ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000
CMD ["python", "-m", "app"]

FROM base AS production
RUN uv sync --frozen --no-dev --no-install-project
COPY --chown=app:app backend/ ./
RUN uv sync --frozen --no-dev && chown -R app:app /app
ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000
CMD ["python", "-m", "app"]

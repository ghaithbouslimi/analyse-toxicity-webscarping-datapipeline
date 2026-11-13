FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    RAYON_NUM_THREADS=1 \
    UV_CONCURRENT_DOWNLOADS=2 \
    UV_CONCURRENT_INSTALLS=1 \
    UV_CONCURRENT_BUILDS=1 \
    TORCH_THREADS=1 \
    MODEL_DTYPE=float16 \
    MODEL_REVISION=4ad6f5c104d9ce813a1a2f33cac0c5b579ef6ee5 \
    MODEL_CACHE_DIR=/app/cache/modeles \
    MPLCONFIGDIR=/tmp/matplotlib
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable --no-cache
COPY configuration ./configuration
RUN useradd --uid 10001 --create-home app \
    && mkdir -p /app/cache/modeles /app/rapports \
    && chown -R app:app /app/cache /app/rapports
USER app
EXPOSE 8000
CMD ["toxicite", "servir"]

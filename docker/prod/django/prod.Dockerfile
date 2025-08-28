# 0.8.13-python3.13-alpine
FROM ghcr.io/astral-sh/uv@sha256:3ce89663b5309e77087de25ca805c49988f2716cdb2c6469b1dec2764f58b141

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apk \
    --mount=type=cache,target=/etc/apk/cache \
    apk update && apk add gcc musl-dev libpq-dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen

COPY . .

# python3.13-alpine
FROM python@sha256:9ba6d8cbebf0fb6546ae71f2a1c14f6ffd2fdab83af7fa5669734ef30ad48844

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apk update && apk add --no-cache libpq tini
RUN addgroup -S django  \
    && addgroup -g 1015 fileserv \
    && adduser -S django -G django -G fileserv --disabled-password

COPY --from=builder --chown=django:django /app /app

RUN mkdir -p /app/media && chown -R :fileserv /app/media && chmod -R 770 /app/media
RUN mkdir -p /app/static && chown -R :fileserv /app/static && chmod -R 770 /app/static

USER django
ENTRYPOINT ["/sbin/tini", "--"]

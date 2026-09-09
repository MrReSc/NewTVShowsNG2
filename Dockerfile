FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    OUTPUT_DIR=/out

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir . \
    && groupadd --system --gid 10001 newtvshows \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent newtvshows \
    && mkdir -p /data /out \
    && chown -R newtvshows:newtvshows /data /out

USER 10001:10001

VOLUME ["/data", "/out"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.getenv('PORT', '8080')}/healthz\", timeout=3)"]

ENTRYPOINT ["newtvshowsng2"]

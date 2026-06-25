FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/mediaforgetool

# nodejs gives yt-dlp a JavaScript runtime for extractors that need one.
RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg nodejs ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY requirements ./requirements
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements/base.txt

COPY app ./app
RUN mkdir -p storage/jobs temp/jobs

EXPOSE 8421

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('APP_PORT', '8421')}/healthz\", timeout=3).read()"

CMD ["python", "-m", "app.run"]

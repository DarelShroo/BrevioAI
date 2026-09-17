FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps + mermaid CLI first so source edits do not invalidate these layers.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libglib2.0-0 \
      tesseract-ocr \
      tesseract-ocr-spa \
      poppler-utils \
      ffmpeg \
      nodejs \
      npm \
      libnss3 \
      libnspr4 \
      libgbm1 \
      libasound2 \
      libatk-bridge2.0-0 \
      libgtk-3-0 \
      libx11-xcb1 \
      libpango-1.0-0 \
      libpangoft2-1.0-0 \
      libharfbuzz0b \
      libgdk-pixbuf-2.0-0 \
      shared-mime-info \
      fontconfig \
      fonts-dejavu-core \
      fonts-noto-core \
      fonts-noto-mono \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_CACHE_DIR=/opt/puppeteer_cache
RUN mkdir -p /opt/puppeteer_cache && chmod 777 /opt/puppeteer_cache && \
    npm install -g @mermaid-js/mermaid-cli@10.9.1 --unsafe-perm=true

# Dependency layer: only invalidated when requirements change.
COPY requirements.txt /app/core/requirements.txt
RUN printf 'setuptools>=83\n' > /tmp/pip-build-constraints.txt && \
    pip install --upgrade pip "setuptools==83.0.0" wheel && \
    pip install --no-cache-dir \
      --build-constraint /tmp/pip-build-constraints.txt \
      -r core/requirements.txt && \
    useradd --create-home --uid 10001 --shell /usr/sbin/nologin brevio && \
    mkdir -p /app/data && \
    chown -R brevio:brevio /app

# Application source last (bind-mounted in docker-compose.dev.yml).
COPY . /app/core
RUN chown -R brevio:brevio /app/core

USER brevio

EXPOSE 8000

CMD ["fastapi", "run", "core/brevio_api/__main__.py", "--port", "8000"]

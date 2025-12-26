FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
# We need these for audio processing/video libraries often used with AI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    git \
    && rm -rf /var/lib/apt/lists/*

# We are already in a python environment, so we don't strictly need a venv, 
# but keeping it is good practice or we can drop it to save a bit of complexity.
# Given the user wants to reduce size/complexity, dropping venv in a container is standard.
# However, if the app relies on /opt/venv path, we should keep it or adjust paths.
# The original dockerfile set PATH. Let's stick to system python to save space/layers?
# Actually, venv protects from system package clashes. Let's keep venv but use the provided python.

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Install ML dependencies (heavy, cached layer)
COPY requirements-ml.txt /app/core/requirements-ml.txt
RUN pip install --no-cache-dir -r /app/core/requirements-ml.txt

# Install app dependencies (cached unless requirements.txt changes)
COPY requirements.txt /app/core/requirements.txt
RUN pip install --no-cache-dir -r /app/core/requirements.txt

# Copy source code (changes frequently, so it's last)
COPY . /app/core

EXPOSE 8000

CMD ["fastapi", "run", "core/brevio_api/__main__.py", "--port", "8000"]
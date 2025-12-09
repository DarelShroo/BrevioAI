FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04

WORKDIR /app

# Install system dependencies first (cached unless changed)
RUN apt-get update && \
    apt-get install -y python3.12 python3.12-venv libglib2.0-0 libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.12 -m venv /opt/venv
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
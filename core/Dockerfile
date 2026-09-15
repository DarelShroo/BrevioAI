FROM python:3.12-slim-bookworm

WORKDIR /app

COPY . /app/core

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libglib2.0-0 \
      tesseract-ocr \
      tesseract-ocr-spa \
      poppler-utils \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip "setuptools<70.0.0" wheel && \
    pip install --no-cache-dir -r core/requirements.txt

EXPOSE 8000

CMD ["fastapi", "run", "core/brevio_api/__main__.py", "--port", "8000"]

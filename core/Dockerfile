FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04

WORKDIR /app

COPY . /app/core

RUN apt-get update && \
    apt-get install -y python3.12 python3.12-venv libglib2.0-0 tesseract-ocr tesseract-ocr-spa poppler-utils && \
    rm -rf /var/lib/apt/lists/*

RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip "setuptools<70.0.0" wheel

RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20240930
RUN pip install --no-cache-dir -r core/requirements.txt

EXPOSE 8000

CMD ["fastapi", "run", "core/brevio_api/__main__.py", "--port", "8000"]
FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04

WORKDIR /app

COPY . /app

RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    libglib2.0-0 \
    yt-dlp

RUN python3 -m venv .venv
RUN source .venv/bin/activate   

RUN pip3 install torch --index-url https://download.pytorch.org/whl/cu118
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["fastapi", "run", "__main__.py", "--port", "8000"]
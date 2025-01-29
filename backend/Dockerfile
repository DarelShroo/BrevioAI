FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04

WORKDIR /app

COPY . /app

RUN apt-get update && \
    apt-get install -y python3 python3-pip libglib2.0-0 yt-dlp && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install torch --index-url https://download.pytorch.org/whl/cu118 --break-system-packages
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

EXPOSE 8000

RUN apt list --installed > /app/packages-system.txt && \
    pip freeze > /app/packages-python.txt

CMD ["fastapi", "run", "__main__.py", "--port", "8000"]
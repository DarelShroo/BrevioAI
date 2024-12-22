FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04

WORKDIR /app

COPY . /app

RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    libglib2.0-0 \
    yt-dlp


RUN pip3 install torch --index-url https://download.pytorch.org/whl/cu118 --break-system-packages
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages
RUN pip3 install "fastapi[standard]" --break-system-packages

EXPOSE 5000

CMD ["python3", "brevio_service/main.py"]

#CMD ["tail", "-f", "/dev/null"]
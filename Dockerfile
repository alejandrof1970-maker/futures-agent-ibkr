# Imagen oficial de IBeam en Docker Hub (no ghcr.io)
FROM voyz/ibeam:latest

USER root
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY main.py /app/main.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

WORKDIR /app
CMD ["/app/start.sh"]

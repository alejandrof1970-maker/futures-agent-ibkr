FROM python:3.11-slim

# Java es requerido por IB Gateway
RUN apt-get update && apt-get install -y \
    default-jre-headless \
    wget \
    unzip \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Instalar ibeam y dependencias en Python limpio
# pip install ibeam crea /usr/local/bin/ibeam correctamente
RUN pip install --no-cache-dir \
    ibeam \
    openai \
    pandas \
    numpy \
    requests \
    python-dotenv \
    urllib3

# Verificar que el binario existe
RUN ls -la /usr/local/bin/ibeam && echo "✅ ibeam OK"

COPY main.py /app/main.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

WORKDIR /app
ENV IBEAM_GATEWAY_BASE_URL=https://localhost:5000

CMD ["/app/start.sh"]

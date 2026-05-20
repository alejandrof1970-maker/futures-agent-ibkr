FROM voyz/ibeam:latest

USER root

# Instalar pip y dependencias Python sin venv (conserva el PATH original con ibeam)
RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir --break-system-packages \
    openai>=1.30.0 \
    pandas>=2.0.0 \
    numpy>=1.26.0 \
    requests>=2.31.0 \
    python-dotenv>=1.0.0 \
    urllib3>=2.0.0

COPY main.py /app/main.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

WORKDIR /app
CMD ["/app/start.sh"]

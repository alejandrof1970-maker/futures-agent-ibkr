# gnzsnz/ib-gateway: IB Gateway headless con Java + IBC preinstalados
FROM gnzsnz/ib-gateway:stable

USER root

# Instalar supervisor (maneja 2 procesos) + Python pip
RUN apt-get update && apt-get install -y supervisor python3-pip && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
RUN pip3 install --break-system-packages \
    ib_insync \
    openai \
    pandas \
    numpy \
    python-dotenv

COPY main.py /app/main.py
COPY supervisord.conf /etc/supervisor/conf.d/agent.conf

# Anular entrypoint original — supervisor maneja todo
ENTRYPOINT []
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/agent.conf"]

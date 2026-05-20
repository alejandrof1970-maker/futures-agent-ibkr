FROM gnzsnz/ib-gateway:stable

USER root

# Supervisor para manejar 2 procesos + pip
RUN apt-get update && apt-get install -y supervisor python3-pip && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    ib_insync openai pandas numpy python-dotenv

COPY main.py /app/main.py
COPY supervisord.conf /etc/supervisor/conf.d/agent.conf

ENTRYPOINT []
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/agent.conf"]

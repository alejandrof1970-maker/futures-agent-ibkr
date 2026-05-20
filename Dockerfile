FROM gnzsnz/ib-gateway:stable

USER root

RUN apt-get update && apt-get install -y supervisor python3-pip && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    ib_insync openai pandas numpy python-dotenv

COPY main.py /app/main.py
COPY gateway_start.sh /app/gateway_start.sh
COPY supervisord.conf /etc/supervisor/conf.d/agent.conf
RUN chmod +x /app/gateway_start.sh

ENTRYPOINT []
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/agent.conf"]

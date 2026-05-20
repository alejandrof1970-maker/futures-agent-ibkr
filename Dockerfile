# voyz/ibeam ya tiene Java + IB Gateway pre-instalados
FROM voyz/ibeam:latest

USER root

# Instalar ibeam como paquete pip en el venv existente (/opt/venv)
# Esto crea /opt/venv/bin/ibeam con todo lo necesario
RUN /opt/venv/bin/pip install --upgrade --no-cache-dir \
    ibeam \
    openai \
    pandas \
    numpy \
    requests \
    python-dotenv \
    urllib3

COPY main.py /app/main.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

WORKDIR /app
CMD ["/app/start.sh"]

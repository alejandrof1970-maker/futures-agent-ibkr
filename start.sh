#!/bin/bash

echo "=== Futures Trading Agent ==="

# ibeam instalado via pip queda en /opt/venv/bin/ibeam
IBEAM_BIN="/opt/venv/bin/ibeam"

if [ ! -f "$IBEAM_BIN" ]; then
    echo "ERROR: $IBEAM_BIN no encontrado tras pip install"
    ls /opt/venv/bin/ 2>/dev/null
    exit 1
fi

echo "Iniciando IBeam desde $IBEAM_BIN ..."
$IBEAM_BIN start &
IBEAM_PID=$!

echo "Esperando autenticación (90 segundos)..."
sleep 90

if ! kill -0 $IBEAM_PID 2>/dev/null; then
    echo "ERROR: IBeam terminó inesperadamente."
    exit 1
fi

echo "Iniciando agente de futuros..."
/opt/venv/bin/python3 /app/main.py

kill $IBEAM_PID 2>/dev/null || true

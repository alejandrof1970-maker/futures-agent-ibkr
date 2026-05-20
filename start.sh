#!/bin/bash

echo "=== Futures Trading Agent ==="
echo "ibeam path: $(which ibeam)"

echo "Iniciando IBeam (la primera vez descarga IB Gateway)..."
ibeam start &
IBEAM_PID=$!

echo "Esperando autenticación (120 segundos)..."
sleep 120

if ! kill -0 $IBEAM_PID 2>/dev/null; then
    echo "ERROR: IBeam terminó inesperadamente."
    exit 1
fi

echo "Iniciando agente de futuros..."
python3 /app/main.py

kill $IBEAM_PID 2>/dev/null || true

#!/bin/bash
set -e

echo "=== Futures Trading Agent ==="
echo "Iniciando IBeam (IB Gateway headless)..."

ibeam &
IBEAM_PID=$!

echo "Esperando autenticación IBeam (90 segundos)..."
sleep 90

if ! kill -0 $IBEAM_PID 2>/dev/null; then
    echo "ERROR: IBeam se cerró inesperadamente."
    exit 1
fi

echo "Iniciando agente de futuros..."
cd /app
python3 main.py

kill $IBEAM_PID 2>/dev/null || true

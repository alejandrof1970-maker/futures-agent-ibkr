#!/bin/bash
set -e

echo "=== Futures Trading Agent ==="
echo "Iniciando IBeam con ruta completa..."

# Ruta directa al binario de ibeam en el venv de la imagen base
/opt/venv/bin/ibeam &
IBEAM_PID=$!

echo "Esperando autenticación IBeam (90 segundos)..."
sleep 90

if ! kill -0 $IBEAM_PID 2>/dev/null; then
    echo "ERROR: IBeam terminó inesperadamente."
    exit 1
fi

echo "Iniciando agente de futuros..."
/opt/venv/bin/python3 /app/main.py

kill $IBEAM_PID 2>/dev/null || true

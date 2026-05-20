#!/bin/bash
set -e

echo "=== Futures Trading Agent ==="
echo "Buscando IBeam..."

# Buscar el binario de ibeam en múltiples ubicaciones
IBEAM_BIN=""
for path in \
    "$(which ibeam 2>/dev/null)" \
    "/usr/local/bin/ibeam" \
    "/home/ibeam/.local/bin/ibeam" \
    "$(find /usr /home -name 'ibeam' -type f 2>/dev/null | head -1)"; do
    if [ -x "$path" ]; then
        IBEAM_BIN="$path"
        break
    fi
done

if [ -z "$IBEAM_BIN" ]; then
    echo "Binario no encontrado, usando python3 -m ibeam..."
    IBEAM_CMD="python3 -m ibeam"
else
    echo "IBeam encontrado en: $IBEAM_BIN"
    IBEAM_CMD="$IBEAM_BIN"
fi

echo "Iniciando IB Gateway headless..."
$IBEAM_CMD &
IBEAM_PID=$!

echo "Esperando autenticación IBeam (90 segundos)..."
sleep 90

if ! kill -0 $IBEAM_PID 2>/dev/null; then
    echo "ERROR: IBeam terminó inesperadamente."
    exit 1
fi

echo "Iniciando agente de futuros..."
python3 /app/main.py

kill $IBEAM_PID 2>/dev/null || true

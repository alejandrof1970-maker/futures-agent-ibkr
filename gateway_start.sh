#!/bin/bash
echo "=== DIAGNÓSTICO GNZSNZ IMAGE ==="
echo "-- /root/ --"
ls /root/ 2>/dev/null || echo "vacío"
echo "-- /home/ --"
ls /home/ 2>/dev/null || echo "vacío"
echo "-- find run_ib_gateway.sh --"
SCRIPT=$(find / -maxdepth 8 -name "run_ib_gateway.sh" -type f 2>/dev/null | head -1)
echo "Encontrado: $SCRIPT"
if [ -n "$SCRIPT" ]; then
    chmod +x "$SCRIPT"
    exec "$SCRIPT"
else
    echo "Script no encontrado. Listando .sh:"
    find /root /home /opt /app -name "*.sh" 2>/dev/null | head -20
    sleep 9999
fi

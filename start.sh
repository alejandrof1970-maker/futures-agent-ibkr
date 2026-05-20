#!/bin/bash
echo "=== DIAGNÓSTICO IBEAM ==="
echo "PATH=$PATH"
echo ""
echo "--- which ibeam ---"
which ibeam 2>&1 || echo "no en PATH"
echo ""
echo "--- find ibeam (hasta 6 niveles) ---"
find / -maxdepth 6 -name "ibeam" -type f 2>/dev/null | head -10
echo ""
echo "--- /usr/local/bin ---"
ls /usr/local/bin/ 2>/dev/null | grep -i beam || echo "ninguno"
echo ""
echo "--- pip show ibeam ---"
pip show ibeam 2>/dev/null || pip3 show ibeam 2>/dev/null || echo "no instalado"
echo "=== FIN ==="

# Ahora intentar iniciar con rutas posibles
for BIN in ibeam /usr/local/bin/ibeam /usr/bin/ibeam; do
    if command -v "$BIN" &>/dev/null || [ -f "$BIN" ]; then
        echo "Encontrado: $BIN — iniciando..."
        "$BIN" start &
        sleep 90
        echo "Iniciando agente..."
        python3 /app/main.py
        exit 0
    fi
done

echo "ERROR: ibeam no encontrado en ninguna ruta conocida"
exit 1

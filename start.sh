#!/bin/bash

# Intervalo en horas (por defecto: 12)
INTERVAL_HOURS=${RUN_INTERVAL_HOURS:-12}
INTERVAL_SECONDS=$((INTERVAL_HOURS * 3600))

echo "[INFO] Iniciando ciclo con intervalo de $INTERVAL_HOURS horas..."

while true; do
    echo "[INFO] Ejecutando limpieza a $(date)"
    python main.py
    echo "[INFO] Esperando $INTERVAL_HOURS horas..."
    sleep $INTERVAL_SECONDS
done

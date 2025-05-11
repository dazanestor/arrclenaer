#!/bin/bash

# Activar el entorno virtual
source /home/appuser/venv/bin/activate

# Log para el inicio
echo "[INFO] Iniciando ciclo con intervalo de ${INTERVAL_HOURS} horas..."

# Ciclo de ejecución
while true; do
    echo "[INFO] Ejecutando limpieza a $(date)"
    python main.py  # Ejecutar el script dentro del entorno virtual
    echo "[INFO] Esperando ${INTERVAL_HOURS} horas..."
    sleep $(($INTERVAL_HOURS * 3600))  # Esperar el intervalo
done

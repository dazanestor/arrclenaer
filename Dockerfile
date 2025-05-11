FROM python:3.11-slim

# Crear un usuario no root
RUN useradd -m appuser

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar archivos necesarios
COPY main.py .
COPY start.sh .

# Cambiar al usuario no root
USER appuser

# Actualizar pip y crear un entorno virtual dentro del directorio del usuario
RUN python -m venv /home/appuser/venv
RUN /home/appuser/venv/bin/pip install --upgrade pip
RUN /home/appuser/venv/bin/pip install requests

# Dar permisos de ejecución a start.sh
RUN chmod +x start.sh

# Usar el entorno virtual para ejecutar start.sh
CMD ["/home/appuser/venv/bin/python", "start.sh"]

FROM python:3.11-slim

# Crear un usuario no root
RUN useradd -m appuser

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar archivos necesarios
COPY main.py .
COPY start.sh .

# Cambiar permisos de start.sh como root
RUN chmod +x start.sh

# Cambiar al usuario no root
USER appuser

# Crear un entorno virtual
RUN python -m venv /home/appuser/venv

# Instalar las dependencias en el entorno virtual
RUN /home/appuser/venv/bin/pip install --upgrade pip
RUN /home/appuser/venv/bin/pip install requests

# Usar el entorno virtual para ejecutar start.sh con Bash
CMD ["/bin/bash", "-c", "source /home/appuser/venv/bin/activate && python main.py"]

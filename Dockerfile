# ─── INMERSIVA — Dockerfile ───────────────────────────────────────────────────
# Imagen base: Python 3.12 en versión liviana (slim)
# "slim" significa que no trae herramientas innecesarias, reduciendo el tamaño final

FROM python:3.12-slim

# Evita que Python genere archivos .pyc (bytecode) innecesarios
ENV PYTHONDONTWRITEBYTECODE=1

# Hace que los logs aparezcan en tiempo real (sin buffer)
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema operativo necesarias para PostgreSQL y Pillow
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements primero (optimiza cache de Docker)
# Si no cambias las dependencias, Docker reutiliza esta capa
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear directorios de trabajo que necesita la app
RUN mkdir -p app/uploads app/generated/pdfs app/generated/social app/generated/temp

# Puerto que expone la aplicación
EXPOSE 8000

# Comando para iniciar el servidor
# --host 0.0.0.0 permite conexiones externas (requerido en Docker)
# --workers 2 para manejar múltiples requests simultáneos
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

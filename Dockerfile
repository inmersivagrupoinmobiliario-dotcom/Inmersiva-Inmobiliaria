# ─── INMERSIVA — Dockerfile ───────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema: WeasyPrint (Pango/Cairo), Pillow, psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    # Pillow
    libjpeg-dev libpng-dev libfreetype6-dev \
    # WeasyPrint
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libcairo2 libgdk-pixbuf-xlib-2.0-0 libffi-dev \
    libxml2 libxslt1.1 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python (capa cacheada separada)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY . .

# Directorios de trabajo en tiempo de ejecución
RUN mkdir -p uploads generated/pdfs generated/images generated/videos generated/temp

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

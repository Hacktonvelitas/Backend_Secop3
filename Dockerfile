FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install -U pip && pip install --no-cache-dir -r requirements.txt

# Copia la carpeta app dentro de /app/app
COPY app ./app

# Create a non-root user and switch to it
RUN addgroup --system appgroup && adduser --system --group appuser
USER appuser

EXPOSE 8000
ENV UVICORN_WORKERS=2 PORT=8000 PYTHONPATH=/app

# Se usa app.main:api porque en main.py la instancia se llama 'api'
CMD ["sh","-lc","uvicorn app.main:api --host 0.0.0.0 --port ${PORT} --workers ${UVICORN_WORKERS}"]

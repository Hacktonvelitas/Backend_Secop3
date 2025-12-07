FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el contenido de la carpeta 'app' al contenedor
COPY app/ .

# Opcional pero útil para imports absolutos tipo "from db import ...":
ENV PYTHONPATH=/

CMD ["uvicorn","main:api","--host","0.0.0.0","--port","8000","--proxy-headers"]

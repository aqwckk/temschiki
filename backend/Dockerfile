FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_EMULATORS_DIR=/app/emulators \
    APP_DATABASE_URL=sqlite:////data/data.db \
    APP_UJIN_CREDENTIALS_FILE=/run/secrets/ujin.json

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY emulators emulators
COPY backend/app backend/app

WORKDIR /app/backend
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

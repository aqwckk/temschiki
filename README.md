# УМКА - умный дом на Ujin OS

## Быстрый старт (Docker)

Нужен Docker с Compose.

```bash
docker compose up -d --build
```

Открыть **http://localhost**. Документация API (Swagger): **http://localhost/docs**.

## Запуск без Docker

Нужны Python 3.11+ и Node.js 20+.

**Бэкенд** (порт 8000):

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

На Windows вместо `.venv/bin/` пишите `.venv\Scripts\`.

**Фронт** (порт 5173, запросы к API проксирует сам):

```bash
cd mobile-prototype
npm ci
npm run dev
```

Открыть **http://localhost:5173**.

## Подключение к Ujin

По умолчанию обмен с Ujin выключен (режим `dry`): все работает локально.

Чтобы включить:

1. Положить файл доступов команды (`доступы.json`):
   - для Docker - в `secrets/ujin.json`;
   - без Docker - в `backend/доступы.json`.
2. Включить режим `live`:
   - для Docker - файл `.env` рядом с `docker-compose.yml`: `UJIN_MODE=live`;
   - без Docker - файл `backend/.env`: `APP_UJIN_MODE=live`.
3. Перезапустить.

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import device_types, devices


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Temschiki Smart Home", lifespan=lifespan)
app.include_router(device_types.router)
app.include_router(devices.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

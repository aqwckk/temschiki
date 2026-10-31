import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import SessionLocal, init_db
from app.emulation.runtime import runtime
from app.errors import register_error_handlers
from app.routers import device_types, devices, journal, scenarios
from app.scenarios.engine import engine
from app.services import devices as device_service
from app.services import scenarios as scenario_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as session:
        device_service.start_all(session)
        engine.start(asyncio.get_running_loop(), scenario_service.list_scenarios(session))
    await runtime.start()
    yield
    await runtime.stop()


app = FastAPI(title="Temschiki Smart Home", lifespan=lifespan)
register_error_handlers(app)
app.include_router(device_types.router)
app.include_router(devices.router)
app.include_router(scenarios.router)
app.include_router(journal.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

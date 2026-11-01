import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import SessionLocal, init_db
from app.emulation.runtime import runtime
from app.errors import register_error_handlers
from app.realtime import events
from app.realtime.hub import hub
from app.routers import device_types, devices, journal, realtime, scenarios, situations, ujin
from app.scenarios.engine import engine
from app.services import device_types as device_type_service
from app.services import devices as device_service
from app.services import emergencies as emergency_service
from app.services import scenarios as scenario_service
from app.services import situations as situation_service
from app.ujin.mirror import mirror


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    loop = asyncio.get_running_loop()
    hub.start(loop)
    mirror.load_credentials()
    runtime.subscribe(events.publish_signal)
    runtime.subscribe(mirror.on_signal)
    with SessionLocal() as session:
        device_type_service.register_all(session)
        situation_service.register_all(session)
        device_service.start_all(session)
        emergency_service.load_all(session)
        engine.start(loop, scenario_service.list_scenarios(session))
    await runtime.start()
    await mirror.start()
    yield
    await mirror.stop()
    await engine.stop()
    await runtime.stop()


app = FastAPI(title="Temschiki Smart Home", lifespan=lifespan)
register_error_handlers(app)
app.include_router(device_types.router)
app.include_router(devices.router)
app.include_router(scenarios.router)
app.include_router(situations.router)
app.include_router(journal.router)
app.include_router(realtime.router)
app.include_router(ujin.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

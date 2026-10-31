from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.emulation.errors import CommandRejected, DeviceNotRunning, DeviceOffline
from app.scenarios.errors import ScenarioInvalid

# доменная ошибка -> HTTP-статус
STATUS_BY_ERROR = {
    DeviceNotRunning: 503,
    DeviceOffline: 409,
    CommandRejected: 400,
    ScenarioInvalid: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    for error_class, status_code in STATUS_BY_ERROR.items():
        app.add_exception_handler(error_class, _make_handler(status_code))


def _make_handler(status_code: int):
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler

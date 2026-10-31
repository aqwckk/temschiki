import asyncio

from fastapi import APIRouter, WebSocket

from app.emulation.runtime import runtime
from app.realtime import events
from app.realtime.hub import hub

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def live_events(websocket: WebSocket):
    await websocket.accept()
    queue = hub.connect()
    sender = asyncio.create_task(_send_events(websocket, queue))
    try:
        await websocket.send_json(events.snapshot(runtime.all_states()))
        await _wait_for_close(websocket)
    finally:
        sender.cancel()
        hub.disconnect(queue)


async def _send_events(websocket: WebSocket, queue: asyncio.Queue) -> None:
    while True:
        event = await queue.get()
        await websocket.send_json(event)


async def _wait_for_close(websocket: WebSocket) -> None:
    # клиенту писать не нужно, слушаем только чтобы заметить отключение
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return

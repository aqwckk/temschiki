"""Рассылка событий всем подключенным WebSocket-клиентам."""
import asyncio
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# сколько событий держим для медленного клиента, дальше старые выбрасываем
QUEUE_SIZE = 1000


class Hub:
    def __init__(self):
        self._queues: set[asyncio.Queue] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def connect(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        with self._lock:
            self._queues.add(queue)
        return queue

    def disconnect(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._queues.discard(queue)

    def publish(self, event: dict) -> None:
        """Можно вызывать из любого потока: событие уходит в цикл сервера."""
        if self._loop is None or self._loop.is_closed():
            return
        with self._lock:
            queues = list(self._queues)
        for queue in queues:
            self._loop.call_soon_threadsafe(_put, queue, event)


def _put(queue: asyncio.Queue, event: dict) -> None:
    if queue.full():
        queue.get_nowait()
    queue.put_nowait(event)


hub = Hub()

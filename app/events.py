import asyncio
from typing import Any, List


class EventBus:
    """Simple in-memory pub/sub using asyncio.Queue for SSE/web subscribers."""

    def __init__(self) -> None:
        self._subs: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subs.remove(q)
        except ValueError:
            pass

    def publish(self, data: Any) -> None:
        # Non-blocking fan-out; drop if subscriber queue is full (unlikely with default size)
        for q in list(self._subs):
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                # Skip slow consumer
                pass


"""Bounded process-local event queue."""

import asyncio
from dataclasses import dataclass
from datetime import datetime

from pydantic import JsonValue


@dataclass(frozen=True, slots=True)
class EngineEvent:
    """Describe an internal monitoring event."""

    name: str
    timestamp: datetime
    payload: dict[str, JsonValue]


class EventBus:
    """Apply backpressure rather than silently dropping monitoring events."""

    def __init__(self, maxsize: int = 1024) -> None:
        """Allocate a bounded asynchronous queue."""
        if maxsize <= 0:
            raise ValueError("maxsize must be positive.")

        self._queue: asyncio.Queue[EngineEvent] = asyncio.Queue(maxsize=maxsize)

    async def publish(self, event: EngineEvent) -> None:
        """Wait until an event can enter the queue."""
        await self._queue.put(event)

    async def receive(self) -> EngineEvent:
        """Wait for and return the next event."""
        return await self._queue.get()

    def task_done(self) -> None:
        """Mark the most recently handled event as complete."""
        self._queue.task_done()

    async def join(self) -> None:
        """Wait until queued events have been acknowledged."""
        await self._queue.join()

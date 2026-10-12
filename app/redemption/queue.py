
import asyncio

from app.redemption.base import RedemptionJob


class RedemptionQueue:
    def __init__(self):
        self._queue: asyncio.Queue[RedemptionJob] = asyncio.Queue()

    async def put(self, job: RedemptionJob) -> None:
        await self._queue.put(job)

    async def get(self) -> RedemptionJob:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()

    def size(self) -> int:
        return self._queue.qsize()


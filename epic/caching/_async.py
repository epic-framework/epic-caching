import asyncio
import inspect
from typing import TypeVar, Generic
from collections.abc import Awaitable

T = TypeVar('T')


class CachedAwaitableRunner(Generic[T]):
    """Given an Awaitable, allow await-ing it multiple times by running it once and caching the result.
    The original coroutine is lazily started only upon the first all to `cached_run`.

    This class enables caching of async functions, which don't return values but instead coroutines which can only be
    awaited once.
    """
    def __init__(self, awaitable: Awaitable[T]):
        self.awaitable = awaitable
        self.task = None
        self.shared_future = None
        self.start_lock = asyncio.Lock()

    async def cached_run(self) -> T:
        if self.task is None:
            async with self.start_lock:
                if self.task is None:
                    self.shared_future = asyncio.get_running_loop().create_future()
                    self.task = asyncio.create_task(self._run())
        return await self.shared_future

    async def _run(self):
        try:
            result = await self.awaitable
            if not self.shared_future.done():
                self.shared_future.set_result(result)
        except Exception as e:
            if not self.shared_future.done():
                self.shared_future.set_exception(e)


def requires_async_caching(func):
    return inspect.iscoroutinefunction(func)

import asyncio
import inspect
from typing import Awaitable, TypeVar, Generic

T = TypeVar('T')


class CoroutineFactory(Generic[T]):
    """A factory for 'secondary' coroutines that, when awaited, each return the result of a 'primary' coroutine.
    This enables caching of async functions, which don't return values but instead coroutines which can only be
    awaited once.
    The primary coroutine is lazily started only when one of the secondary coroutines is started.
    """
    def __init__(self, coroutine: Awaitable[T]):
        self.primary = coroutine
        self.shared_future = asyncio.Future()
        self.primary_started = False
        self.start_lock = asyncio.Lock()

    async def _run_primary(self):
        try:
            result = await self.primary
            if not self.shared_future.done():
                self.shared_future.set_result(result)
        except Exception as e:
            if not self.shared_future.done():
                self.shared_future.set_exception(e)

    async def make_secondary(self) -> Awaitable[T]:
        if not self.primary_started:
            async with self.start_lock:
                if not self.primary_started:
                    self.primary_started = True
                    asyncio.create_task(self._run_primary())
        return await self.shared_future


def requires_async_caching(func):
    return inspect.iscoroutinefunction(func)

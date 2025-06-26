import time
import random
import asyncio

import pytest

from epic.caching import cached
from epic.caching._async import CachedAwaitableRunner


class SpecificException(Exception):
    """Specific exception subtype to be detected by test"""


class TestCachedAwaitableRunner:
    started_once = False

    @classmethod
    async def async_func(cls, *, should_err=False, mark_started=False):
        if mark_started:
            cls.started_once = True
        if should_err:
            raise SpecificException("error raised from async function")
        return random.random()

    async def test_basic(self):
        value1 = await self.async_func()
        cf = CachedAwaitableRunner(self.async_func())
        value2 = await cf.cached_run()
        value3 = await cf.cached_run()
        assert value1 != value2
        assert value2 == value3

    async def test_lazy_start(self):
        cf = CachedAwaitableRunner(self.async_func(mark_started=True))
        assert not self.started_once
        secondaries = [cf.cached_run() for _ in range(100)]
        random.shuffle(secondaries)
        await asyncio.sleep(0.2)
        assert not self.started_once
        values = await asyncio.gather(*secondaries)
        assert len(set(values)) == 1

    async def test_exceptions(self):
        cf = CachedAwaitableRunner(self.async_func(should_err=True))
        for i in range(5):
            secondaries = [cf.cached_run() for _ in range(5 - i)]
            random.shuffle(secondaries)
            for secondary in secondaries:
                with pytest.raises(SpecificException):
                    await secondary


class TestCachingAsyncFunctions:
    async def test_simple(self):
        started = False

        @cached
        async def func():
            nonlocal started
            started = True
            return random.random()

        assert not started
        f1 = func()
        assert not started
        a = await f1
        assert started
        b = await func()
        assert a == b

    async def test_async_method(self):
        call_count = 0

        class ClassWithAsyncMethod:
            @cached
            async def random_value(self):
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0.1)
                return random.random()

        instance0 = ClassWithAsyncMethod()
        value0 = await instance0.random_value()
        assert value0 == await instance0.random_value()

        call_count = 0
        instance1 = ClassWithAsyncMethod()
        instance2 = ClassWithAsyncMethod()
        assert call_count == 0
        future1 = instance1.random_value()
        future2 = instance2.random_value()
        assert call_count == 0
        value1 = await future1
        assert call_count == 1
        assert value1 == await instance1.random_value()
        assert call_count == 1
        value2 = await future2
        assert call_count == 2
        assert value2 == await instance2.random_value()
        assert call_count == 2

    async def test_timing(self):
        @cached
        async def async_sleep(interval):
            await asyncio.sleep(interval)

        t0 = time.time()
        await async_sleep(0.1)
        await async_sleep(0.1)
        assert time.time() - t0 < 0.15

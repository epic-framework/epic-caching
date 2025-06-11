import pytest
import random
import asyncio
from epic.caching._async import CoroutineFactory

class MyException(Exception):
    """Specific exception to be detected by test"""


class TestCoroutineFactory:
    started_once = False

    @classmethod
    async def async_func(cls, *, should_err=False, mark_started=False):
        if mark_started:
            cls.started_once = True
        if should_err:
            raise MyException("error raised from async function")
        return random.random()

    async def test_basic(self):
        value1 = await self.async_func()
        cf = CoroutineFactory(self.async_func())
        value2 = await cf.make_secondary()
        value3 = await cf.make_secondary()
        assert value1 != value2
        assert value2 == value3

    async def test_lazy_start(self):
        cf = CoroutineFactory(self.async_func(mark_started=True))
        assert not self.started_once
        secondaries = [cf.make_secondary() for _ in range(100)]
        random.shuffle(secondaries)
        await asyncio.sleep(0.2)
        assert not self.started_once
        values = await asyncio.gather(*secondaries)
        assert len(set(values)) == 1

    async def test_exceptions(self):
        cf = CoroutineFactory(self.async_func(should_err=True))
        for i in range(5):
            secondaries = [cf.make_secondary() for _ in range(5 - i)]
            random.shuffle(secondaries)
            for secondary in secondaries:
                with pytest.raises(MyException):
                    await secondary

import pytest
from anyio import create_task_group
from pydantic import BaseModel

from llegos import dev as llegos

pytestmark = pytest.mark.anyio


class Counter(BaseModel):
    count: int = 0

    def increment(self):
        self.count += 1


async def test_counter():
    async with create_task_group() as tg:
        counter = llegos.GenAgent(state=Counter())
        tg.start_soon(counter.start)

        count = (await counter.get_state()).count
        assert count == 0

        await counter.update_state(lambda c: c.increment())
        count = (await counter.get_state()).count
        assert count == 1

        def update_fn(c: Counter):
            c.increment()
            return c.count

        count = await counter.get_and_update_state(update_fn)
        assert count == 2

        tg.cancel_scope.cancel()


async def test_counters():
    counter1 = llegos.GenAgent(state=Counter())
    counter2 = llegos.GenAgent(state=Counter())

    async with create_task_group() as tg:
        tg.start_soon(counter1.start)
        tg.start_soon(counter2.start)

        count1 = (await counter1.get_state()).count
        count2 = (await counter2.get_state()).count
        assert count1 == 0
        assert count2 == 0

        from operator import methodcaller

        tg.start_soon(counter1.update_state, methodcaller("increment"))
        tg.start_soon(counter2.update_state, methodcaller("increment"))

        await counter1.stop()
        await counter2.stop()

    count1 = counter1.state.count
    count2 = counter2.state.count
    assert count1 == 1
    assert count2 == 1

import pytest
from asyncstdlib.builtins import list
from asyncstdlib.itertools import islice
from matchref import ref

from llegos import development as llegos


class Ping(llegos.Message):
    ...


class Pinger(llegos.AsyncActor):
    async def receive_ping(self, ping: Ping) -> "Pong":
        return Pong.reply_to(ping)


class Pong(llegos.Message):
    ...


class Ponger(llegos.AsyncActor):
    async def receive_pong(self, pong: Pong) -> "Ping":
        return Ping.reply_to(pong)


def test_actor_can_receive() -> None:
    pinger = Pinger()
    ponger = Ponger()

    assert not pinger.can_receive(Pong)
    assert not ponger.can_receive(Ping)
    assert pinger.can_receive(Ping)
    assert ponger.can_receive(Pong)


@pytest.mark.asyncio
async def test_ping_pong() -> None:
    """
    Test two actors sending messages to each other indefinitely.
    """

    pinger = Pinger()
    ponger = Ponger()

    msg = Ping(sender=ponger, receiver=pinger)
    async for reply in llegos.message_send(msg):
        match reply:
            case Pong(sender=ref.pinger, receiver=ref.ponger):
                ...
            case _:
                assert False, reply

    msg = Pong(sender=pinger, receiver=ponger)
    async for reply in llegos.message_send(msg):
        match reply:
            case Ping(sender=ref.ponger, receiver=ref.pinger):
                ...
            case _:
                assert False, reply


@pytest.mark.asyncio
async def test_actor_callbacks() -> None:
    counter = 0

    def incr():
        nonlocal counter
        counter += 1

    pinger = Pinger()
    await pinger.on("before:receive", lambda _: incr())
    ponger = Ponger()
    await ponger.on("before:receive", lambda _: incr())

    message_chain = llegos.message_propogate(Ping(sender=ponger, receiver=pinger))

    await list(islice(message_chain, 2))
    assert counter == 2

    await list(islice(message_chain, 1))
    assert counter == 3

    await list(islice(message_chain, 7))
    assert counter == 10

from typing import AsyncIterable, Optional

from aiometer import amap
from networkx import DiGraph
from pyee import AsyncIOEventEmitter

from gen_net.agents import Field, GenAgent, Message


class AsyncGenAgent(GenAgent):
    event_emitter: AsyncIOEventEmitter = Field(
        default_factory=AsyncIOEventEmitter, init=False
    )

    async def receive(self, message: Message) -> AsyncIterable[Message]:
        if message is None or message.sender == self or message.receiver != self:
            raise StopAsyncIteration

        self.emit("receive", message)

        generator = getattr(self, message.method)
        async for reply in generator(message):
            if (yield reply) is StopAsyncIteration:
                break
            self.emit("reply", reply)


async def dispatch(message: Message) -> AsyncIterable[Message]:
    agent: Optional[AsyncGenAgent] = message.receiver
    if not agent:
        raise StopAsyncIteration
    response = agent.receive(message)
    match response:
        case AsyncIterable():
            async for l1 in response:
                if (yield l1) is StopAsyncIteration:
                    break
        case _:
            l1 = await response
            if l1:
                yield l1


async def propogate(message: Message) -> AsyncIterable[Message]:
    async for l1 in dispatch(message):
        if (yield l1) is StopAsyncIteration:
            break
        async for l2 in propogate(l1):
            if (yield l2) is StopAsyncIteration:
                break


async def propogate_all(messages: list[Message]):
    async with amap(propogate, messages) as generators:
        async for gen in generators:
            async for reply in gen:
                if (yield reply) is StopAsyncIteration:
                    break


async def messages_to_graph(messages: AsyncIterable[Message]) -> DiGraph:
    g = DiGraph()
    async for message in messages:
        if message.reply:
            g.add_edge(message.reply, message)
    return g

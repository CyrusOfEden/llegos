from typing import AsyncIterable, Optional

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


async def apply(message: Message) -> AsyncIterable[Message]:
    agent: Optional[AsyncGenAgent] = message.receiver
    if not agent:
        return
    async for l1 in agent.receive(message):
        yield l1
        async for l2 in apply(l1):
            yield l2


async def messages_to_graph(messages: AsyncIterable[Message]) -> DiGraph:
    g = DiGraph()
    async for message in messages:
        if message.reply:
            g.add_edge(message.reply, message)
    return g

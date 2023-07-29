from contextvars import ContextVar
from functools import partial
from typing import Any, AsyncIterable, Optional

import ray

from llegos.asyncio import (
    AsyncAgent,
    AsyncReply,
    EphemeralMessage,
    async_propogate,
    async_propogate_all,
)

actor_namespace = ContextVar("actor_namespace", default="llegos.actors.ns")


class ActorAgent(AsyncAgent):
    @property
    def actor(self):
        ns = actor_namespace.get()
        id = self.id
        return Actor.options(namespace=ns, name=id, get_if_exists=True).remote(self)


@ray.remote(max_restarts=3, max_task_retries=3)
class Actor:
    agent: ActorAgent

    def __init__(self, agent: AsyncAgent):
        self.agent = agent

    def property(self, prop: str) -> Any:
        return getattr(self.agent, prop)

    @ray.method(num_returns="dynamic")
    async def receive(self, message: EphemeralMessage) -> AsyncReply[EphemeralMessage]]:
        async for reply in self.agent.receive(message):
            yield reply


async def actor_apply(message: EphemeralMessage) -> AsyncIterable[EphemeralMessage]:
    agent: Optional[ActorAgent] = message.receiver
    if not agent:
        raise StopAsyncIteration
    async for reply_l1 in agent.actor.receive.remote(message):
        yield reply_l1


actor_propogate = partial(async_propogate, applicator=actor_apply)
actor_propogate_all = partial(async_propogate_all, applicator=actor_apply)

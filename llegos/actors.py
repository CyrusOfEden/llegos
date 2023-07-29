from contextlib import contextmanager
from contextvars import ContextVar
from functools import partial
from typing import Any, AsyncIterable, Iterable, Optional

import ray

from llegos.asyncio import (
    AsyncAgent,
    EphemeralMessage,
    async_propogate,
    async_propogate_all,
)

actor_namespace = ContextVar("actor_namespace", default="llegos.actors.ns")


class ActorAgent(AsyncAgent):
    @contextmanager
    def get_actor(self):
        ns = actor_namespace.get()
        id = str(self.id)
        yield Actor.options(namespace=ns, name=id, get_if_exists=True).remote(self)


@ray.remote(max_restarts=3, max_task_retries=3)
class Actor:
    agent: ActorAgent

    def __init__(self, agent: AsyncAgent):
        self.agent = agent

    def property(self, prop: str) -> Any:
        return getattr(self.agent, prop)

    @ray.method(num_returns="streaming")
    async def receive(
        self, message: EphemeralMessage
    ) -> AsyncIterable[EphemeralMessage]:
        async for reply in self.agent.receive(message):
            yield reply


async def actor_apply(message: EphemeralMessage) -> Iterable[EphemeralMessage]:
    agent: Optional[ActorAgent] = message.receiver
    if not agent:
        return
    with agent.get_actor() as actor:
        async for reply_ref in actor.receive.remote(message):
            reply = await reply_ref
            yield reply


actor_propogate = partial(async_propogate, applicator=actor_apply)
actor_propogate_all = partial(async_propogate_all, applicator=actor_apply)

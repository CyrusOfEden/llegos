from typing import Optional

import ray
from pydantic import Field

from llambdao import AbstractAgent, AgentDispatcher, Message


@ray.remote(max_task_retries=3)
class Actor:
    agent: AbstractAgent

    def __init__(self, agent: AbstractAgent):
        self.agent = agent

    def receive(self, message: Message) -> Optional[Message]:
        return self.agent.receive(message)

    def inform(self, message: Message) -> None:
        self.agent.inform(message)

    def request(self, message: Message) -> Message:
        return self.agent.request(message)


class ActorDispatcher(AgentDispatcher):
    namespace: Optional[str] = Field(default=None)

    def register(self, name: str, agent: AbstractAgent, **metadata):
        actor = Actor.options(
            namespace=self.namespace,
            name=name,
            get_if_exists=True
        ).remote(agent)
        super().register(name, actor, **metadata)

    def dispatch(self, message: Message) -> Message:
        return ray.get(self.future(message))

    def future(self, message: Message) -> ray.ObjectRef[Message]:
        return self.route(message).receive(message)

from abc import ABC
from typing import Any, Dict, Iterable, Optional

import ray

from gpt_net.node import Broadcaster, Field, Message, Node, SystemNode


@ray.remote(max_restarts=3, max_task_retries=3, num_cpus=1)
class Actor:
    node: "ActorNode"

    def __init__(self, node: "ActorNode"):
        self.node = node

    def receive(self, message: Message) -> Optional[Message]:
        """For receiving messages"""
        return self.node.receive(message)

    def property(self, prop: str) -> Any:
        """For getting arbitrary properties on the node"""
        return getattr(self.node, prop)


class ActorNode(Node, ABC):
    """
    Turn a node into a concurrent actor running in its own process.
    Learn more: https://docs.ray.io/en/latest/actors.html

    Can be mixed in with ActorNode to create an actor that runs in its own event loop.
    """

    namespace: Optional[str] = None
    actor_options: Dict = Field(default_factory=dict)

    @property
    def actor(self) -> Actor:
        return Actor.options(
            namespace=self.namespace,
            name=self.id,
            get_if_exists=True,
            **self.actor_options,
        ).remote(self)


class ActorBroadcaster(Broadcaster, ActorNode):
    def receive(self, message: Message) -> Iterable[Message]:
        sender = message.sender
        futures = [
            edge.node.actor.receive.remote(message)
            for edge in self.links.values()
            if edge.node != sender
        ]
        while any(futures):
            ready, futures = ray.wait(futures, num_returns=1)
            for response_messages in ready:
                for message in ray.get(response_messages):
                    yield message


class ActorGroupChat(SystemNode):
    """
    Useful to have multiple actors run in different processes simultaneously.
    Every received chat message will be broadcasted to all nodes except the sender.
    There's no guarantee that the messages will be returned or processed in order.

    This Actor variant can be useful to unlock parallelism without having to use asyncio.
    """

    def chat(self, message: Message):
        messages = [message]
        cursor = 0
        while cursor < len(messages):
            message_i = messages[cursor]
            futures = [
                edge.node.actor.receive.remote(message_i)
                for edge in self.links.values()
                if edge.node.id != message_i.from_id
            ]

            while True:
                ready, in_progress = ray.wait(futures)
                if ready:
                    for message_j in ready:
                        yield message_j
                        messages.append(message_j)
                if not in_progress:
                    break

            cursor += 1

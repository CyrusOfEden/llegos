from abc import ABC
from typing import Any, Dict, Iterable, List, Optional

import ray
from pydantic import Field

from llambdao.base import GraphNode, Node, SwarmNode
from llambdao.message import Message


@ray.remote(max_task_retries=3, num_cpus=1)
class Actor:
    """
    An internal class for wrapping a Node
    """

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


class ActorGraph(GraphNode, ABC):
    def __init__(self, graph: Dict[ActorNode, List[ActorNode]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)
            node.link(self)

            for edge in edges:
                node.link(edge)
                edge.link(node)


class ActorMapperNode(SwarmNode, ActorNode):
    def do(self, message: Message) -> Iterable[Message]:
        sender = message.sender
        futures = [
            edge.node.actor.receive.remote(message)
            for edge in self.edges.values()
            if edge.node != sender
        ]
        while any(futures):
            ready, futures = ray.wait(futures, num_returns=1)
            for response_messages in ready:
                for message in ray.get(response_messages):
                    yield message


class ActorGroupChatNode(ActorMapperNode):
    """
    Useful to have multiple actors run in different processes simultaneously.
    Every received chat message will be broadcasted to all nodes except the sender.
    There's no guarantee that the messages will be processed in order.

    This Actor variant can be useful to unlock parallelism without having to use asyncio.
    """

    def chat(self, message: Message):
        messages = [message]
        while message_i := messages.pop():
            for message_j in self.do(message_i):
                message_j.reply_to = message_i
                yield message_j
                messages.append(message_j)

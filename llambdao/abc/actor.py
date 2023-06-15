from abc import ABC
from typing import Dict, Iterable, List, Optional

import ray

from llambdao.abc import Graph, MapReduce, Message, Node, StableChat
from llambdao.actor import Actor


class ActorNode(Node, ABC):
    """
    Turn a node into a concurrent actor running in its own process.
    Learn more: https://docs.ray.io/en/latest/actors.html

    Can be mixed in with ActorNode to create an actor that runs in its own event loop.
    """

    def actor(self, namespace: Optional[str] = None) -> Actor:
        return Actor.options(
            namespace=namespace, name=self.id, get_if_exists=True
        ).remote(self)


class ActorGraph(Graph, ABC):
    def __init__(self, graph: Dict[ActorNode, List[ActorNode]], **kwargs):
        super().__init__(**kwargs)
        for node, edges in graph.items():
            self.link(node)
            node.link(self)

            for edge in edges:
                node.link(edge)
                edge.link(node)


class ActorMapReduce(MapReduce, ActorNode):
    def request(self, message: Message) -> Iterable[Message]:
        return self._reduce(message, self._map(message))

    def _map(self, message: Message) -> Iterable[Message]:
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

    def _reduce(
        self, message: Message, messages: Iterable[Message]
    ) -> Iterable[Message]:
        yield message
        yield from messages


class ActorUnstableChat(StableChat):
    """
    Useful to have multiple actors run in different processes simultaneously.
    Every received chat message will be broadcasted to all nodes except the sender.
    There's no guarantee that the messages will be processed in order.

    This Unstable Actor variant can be useful to unlock parallelism without having to use asyncio.
    And there's no point to having a StableActorChat because you can just use StableChat.
    """

    def chat(self, message: Message):
        messages = [message]
        while message_i := messages.pop():
            futures = [
                edge.node.actor.receive.remote(message_i)
                for edge in self.edges.values()
                if edge.node != message_i.sender
            ]
            while any(futures):
                ready, futures = ray.wait(futures, num_returns=1)
                for response_messages in ready:
                    for message_j in ray.get(response_messages):
                        message_j.reply_to = message_i
                        yield message_j
                        messages.append(message_j)

                        message_i = message_j

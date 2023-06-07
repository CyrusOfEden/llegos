from abc import ABC
from typing import Optional

from llambdao.abc import Node
from llambdao.actor import Actor


class ActorNode(Node, ABC):
    """
    Turn a node into a concurrent actor running in its own process.
    Learn more: https://docs.ray.io/en/latest/actors.html

    Can be mixed in with AsyncNode to create an actor that runs in its own event loop.
    """

    def actor(self, namespace: Optional[str] = None) -> Actor:
        return Actor.options(
            namespace=namespace, name=self.id, get_if_exists=True
        ).remote(self)
